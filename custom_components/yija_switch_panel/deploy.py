"""Deploy bundled ZHA quirk files into Home Assistant's config/custom_quirks directory."""

from __future__ import annotations

from pathlib import Path
import logging
import re
import shutil

from homeassistant.core import HomeAssistant
import zhaquirks

from .const import (
    DOMAIN,
    MANAGED_QUIRK_FILES,
    QUIRKS_DIR,
    ZHA_CUSTOM_QUIRKS_PATH,
)

_LOGGER = logging.getLogger(__name__)
_ZHA_BLOCK_RE = re.compile(r"^zha:\s*(?:#.*)?$")
_ZHA_INLINE_RE = re.compile(r"^zha:\s+\S+")
_ENABLE_QUIRKS_RE = re.compile(r"^\s*enable_quirks:\s*(true|false)\s*(?:#.*)?$")
_CUSTOM_QUIRKS_RE = re.compile(r"^\s*custom_quirks_path:\s*(.+?)\s*(?:#.*)?$")
_REQUIRED_ZHA_CONFIG = (
    "zha:\n"
    "  enable_quirks: true\n"
    f"  custom_quirks_path: {ZHA_CUSTOM_QUIRKS_PATH}"
)


async def async_deploy_quirks(hass: HomeAssistant) -> None:
    """Copy bundled quirk files into the active HA config directory."""
    config_dir = hass.config.path()
    updated, valid = await hass.async_add_executor_job(
        _ensure_zha_custom_quirks_config,
        config_dir,
    )
    if updated:
        _LOGGER.warning(
            "%s updated configuration.yaml with zha custom quirks settings; restart Home Assistant to let ZHA load quirks during startup",
            DOMAIN,
        )
    elif not valid:
        _LOGGER.warning(
            "%s quirks may fail to load because configuration.yaml does not contain the required ZHA quirk settings. Please check configuration.yaml and add:\n%s",
            DOMAIN,
            _REQUIRED_ZHA_CONFIG,
        )
    await hass.async_add_executor_job(_deploy_quirks, config_dir)
    await hass.async_add_executor_job(_reload_quirk_registry, config_dir)


def _resolve_target_dir(config_dir: str) -> Path:
    """Resolve the effective custom quirks directory for the current HA runtime."""
    config_path = Path(config_dir)
    quirks_path = Path(QUIRKS_DIR)
    if quirks_path.parts[:1] == ("config",) and config_path.name == "config":
        return config_path / Path(*quirks_path.parts[1:])
    return config_path / quirks_path


def _ensure_zha_custom_quirks_config(config_dir: str) -> tuple[bool, bool]:
    """Ensure configuration.yaml enables ZHA quirks and points to custom quirks."""
    config_path = Path(config_dir) / "configuration.yaml"
    desired_block = [
        "zha:",
        "  enable_quirks: true",
        f"  custom_quirks_path: {ZHA_CUSTOM_QUIRKS_PATH}",
    ]

    if not config_path.exists():
        config_path.write_text("\n".join(desired_block) + "\n", encoding="utf-8")
        _LOGGER.warning("%s created configuration.yaml with zha custom quirks settings", DOMAIN)
        return True, True

    original = config_path.read_text(encoding="utf-8")
    updated = _update_configuration_yaml(original)
    if updated is None:
        return False, _has_required_zha_config(original)
    if updated == original:
        return False, True

    backup_path = config_path.with_suffix(f"{config_path.suffix}.{DOMAIN}.bak")
    if not backup_path.exists():
        shutil.copyfile(config_path, backup_path)
        _LOGGER.warning("%s backed up configuration.yaml to %s", DOMAIN, backup_path)

    config_path.write_text(updated, encoding="utf-8")
    return True, True


def _update_configuration_yaml(text: str) -> str | None:
    """Return updated YAML text or None when the file cannot be safely edited."""
    lines = text.splitlines()

    start = None
    for index, line in enumerate(lines):
        if _ZHA_BLOCK_RE.match(line):
            start = index
            break
        if _ZHA_INLINE_RE.match(line):
            _LOGGER.warning(
                "%s could not auto-update configuration.yaml because zha uses an inline or include-based declaration: %s",
                DOMAIN,
                line.strip(),
            )
            return None

    if start is None:
        appended = lines[:]
        if appended and appended[-1].strip():
            appended.append("")
        appended.extend(
            [
                "zha:",
                "  enable_quirks: true",
                f"  custom_quirks_path: {ZHA_CUSTOM_QUIRKS_PATH}",
            ]
        )
        return "\n".join(appended) + "\n"

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line and not line.startswith((" ", "\t", "#")):
            end = index
            break

    block = lines[start:end]
    updated_block = _update_zha_block(block)
    if updated_block == block:
        return text

    merged = lines[:start] + updated_block + lines[end:]
    return "\n".join(merged) + ("\n" if text.endswith("\n") or merged else "")


def _update_zha_block(block: list[str]) -> list[str]:
    """Ensure the zha block contains the desired quirk settings."""
    updated = block[:1]
    saw_enable_quirks = False
    saw_custom_quirks = False

    for line in block[1:]:
        if _ENABLE_QUIRKS_RE.match(line):
            updated.append("  enable_quirks: true")
            saw_enable_quirks = True
            continue
        if _CUSTOM_QUIRKS_RE.match(line):
            updated.append(f"  custom_quirks_path: {ZHA_CUSTOM_QUIRKS_PATH}")
            saw_custom_quirks = True
            continue
        updated.append(line)

    if not saw_enable_quirks:
        updated.append("  enable_quirks: true")
    if not saw_custom_quirks:
        updated.append(f"  custom_quirks_path: {ZHA_CUSTOM_QUIRKS_PATH}")
    return updated


def _has_required_zha_config(text: str) -> bool:
    """Return True when the YAML text already contains the required ZHA settings."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if _ZHA_BLOCK_RE.match(line):
            start = index
            break

    if start is None:
        return False

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line and not line.startswith((" ", "\t", "#")):
            end = index
            break

    saw_enable_quirks = False
    saw_custom_quirks = False
    for line in lines[start + 1:end]:
        enable_match = _ENABLE_QUIRKS_RE.match(line)
        if enable_match and enable_match.group(1) == "true":
            saw_enable_quirks = True
        custom_match = _CUSTOM_QUIRKS_RE.match(line)
        if custom_match and custom_match.group(1).strip() == ZHA_CUSTOM_QUIRKS_PATH:
            saw_custom_quirks = True

    return saw_enable_quirks and saw_custom_quirks


def _deploy_quirks(config_dir: str) -> None:
    """Synchronously deploy bundled quirk files on disk."""
    package_dir = Path(__file__).resolve().parent
    source_dir = package_dir / "quirks"
    target_dir = _resolve_target_dir(config_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for filename in MANAGED_QUIRK_FILES:
        source = source_dir / filename
        target = target_dir / filename

        if not source.exists():
            _LOGGER.warning(
                "%s quirk deploy skipped, bundled file missing: %s",
                DOMAIN,
                source,
            )
            continue

        source_bytes = source.read_bytes()
        if target.exists() and target.read_bytes() == source_bytes:
            continue

        shutil.copyfile(source, target)
        _LOGGER.warning("%s deployed bundled quirk: %s", DOMAIN, target)


def _reload_quirk_registry(config_dir: str) -> None:
    """Force zhaquirks to reload built-in and custom quirk modules."""
    custom_quirks_path = str(_resolve_target_dir(config_dir))
    zhaquirks.setup(custom_quirks_path)
    _LOGGER.warning("%s reloaded zhaquirks using %s", DOMAIN, custom_quirks_path)
