"""Deploy bundled ZHA quirk files into Home Assistant's config/custom_quirks directory."""

from __future__ import annotations

from pathlib import Path
import logging
import shutil

from homeassistant.core import HomeAssistant
import zhaquirks

from .const import DOMAIN, MANAGED_QUIRK_FILES, QUIRKS_DIR

_LOGGER = logging.getLogger(__name__)


async def async_deploy_quirks(hass: HomeAssistant) -> None:
    """Copy bundled quirk files into the active HA config directory."""
    config_dir = hass.config.path()
    await hass.async_add_executor_job(_deploy_quirks, config_dir)
    await hass.async_add_executor_job(_reload_quirk_registry, config_dir)


def _resolve_target_dir(config_dir: str) -> Path:
    """Resolve the effective custom quirks directory for the current HA runtime."""
    config_path = Path(config_dir)
    quirks_path = Path(QUIRKS_DIR)
    if quirks_path.parts[:1] == ("config",) and config_path.name == "config":
        return config_path / Path(*quirks_path.parts[1:])
    return config_path / quirks_path


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
