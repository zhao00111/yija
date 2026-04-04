"""Background sync of HA switch names to Tuya relay screen labels."""

from __future__ import annotations

from datetime import timedelta
import logging
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
import zigpy.types as t
from zhaquirks.tuya import TuyaCommand, TuyaDatapointData, TuyaData
from zhaquirks.tuya import TuyaDPType

from .const import (
    DOMAIN,
    RELAY_ATTRS,
    RELAY_ATTR_NAMES,
    RELAY_NAME_ENCODING,
    SCAN_INTERVAL_SECONDS,
    TARGET_MANUFACTURERS,
    TARGET_MODEL,
    TUYA_CLUSTER_ID,
    TUYA_CLUSTER_TYPE,
    TUYA_ENDPOINT_ID,
    ZHA_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
_RELAY_INDEX_RE = re.compile(r"(?:^|[_\s-])([1-4])$")


async def async_setup_manager(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up the background relay-name sync manager."""
    manager = RelayNameSyncManager(hass, entry.entry_id)
    await manager.async_initial_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager


async def async_unload_manager(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unload the background relay-name sync manager."""
    manager = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if manager is not None:
        await manager.async_unload()

    if hass.data.get(DOMAIN) == {}:
        hass.data.pop(DOMAIN, None)


class RelayNameSyncManager:
    """Discover matching relays and keep them synced with switch names."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._relay_syncs: dict[str, RelayNameSync] = {}
        self._unsubscribe_interval = None

    async def async_initial_setup(self) -> None:
        """Run initial discovery and schedule periodic rescans."""
        await self.async_discover_relays()
        self._unsubscribe_interval = async_track_time_interval(
            self.hass,
            self._async_handle_interval,
            timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )

    async def async_unload(self) -> None:
        """Unload listeners."""
        if self._unsubscribe_interval is not None:
            self._unsubscribe_interval()
            self._unsubscribe_interval = None

        for sync in self._relay_syncs.values():
            await sync.async_unload()
        self._relay_syncs.clear()

    async def _async_handle_interval(self, _now) -> None:
        """Periodic discovery callback."""
        await self.async_discover_relays()

    async def async_discover_relays(self) -> None:
        """Discover matching ZHA devices and attach relay-name sync listeners."""
        device_registry = dr.async_get(self.hass)

        for device in device_registry.devices.values():
            if device.manufacturer not in TARGET_MANUFACTURERS:
                continue
            if device.model != TARGET_MODEL:
                continue

            ieee = _extract_zha_ieee(device)
            if ieee is None:
                continue

            for relay_index, attr_id in RELAY_ATTRS.items():
                unique_id = f"{ieee}-relay_sync_{relay_index}"
                if unique_id in self._relay_syncs:
                    continue

                relay_sync = RelayNameSync(
                    hass=self.hass,
                    ieee=ieee,
                    relay_index=relay_index,
                    attr_id=attr_id,
                )
                attached = await relay_sync.async_setup()
                if attached:
                    self._relay_syncs[unique_id] = relay_sync


class RelayNameSync:
    """Mirror a HA switch entity name to the Tuya relay display."""

    def __init__(self, hass: HomeAssistant, ieee: str, relay_index: int, attr_id: int) -> None:
        self.hass = hass
        self._ieee = ieee
        self._relay_index = relay_index
        self._attr_id = attr_id
        self._attr_name_id = RELAY_ATTR_NAMES[relay_index]
        self._switch_entity_id: str | None = None
        self._last_synced_switch_name: str | None = None
        self._unsubscribe_switch_name = None

    async def async_setup(self) -> bool:
        """Attach to the matching switch entity."""
        switch_entity_id = _find_switch_entity_id(self.hass, self._ieee, self._relay_index)
        if switch_entity_id is None:
            _LOGGER.debug(
                "No matching switch entity found for %s relay %s",
                self._ieee,
                self._relay_index,
            )
            return False

        self._switch_entity_id = switch_entity_id
        self._unsubscribe_switch_name = async_track_state_change_event(
            self.hass,
            [switch_entity_id],
            self._async_handle_switch_name_change,
        )

        if state := self.hass.states.get(switch_entity_id):
            self.hass.async_create_task(
                self._async_sync_from_switch_name(state.name, reason="initial"),
                name=f"tuya_relay_name_initial_{self._relay_index}",
            )

        return True

    async def async_unload(self) -> None:
        """Detach listeners."""
        if self._unsubscribe_switch_name is not None:
            self._unsubscribe_switch_name()
            self._unsubscribe_switch_name = None

    async def _async_handle_switch_name_change(self, event) -> None:
        """Mirror HA switch friendly_name changes to the panel label."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        await self._async_sync_from_switch_name(new_state.name, reason="state_changed")

    async def _async_sync_from_switch_name(self, switch_name: str | None, reason: str) -> None:
        """Push the current HA switch display name to the device when it changes."""
        if not switch_name:
            return

        if switch_name == self._last_synced_switch_name and reason != "initial":
            return

        try:
            await _async_write_relay_name(
                self.hass,
                self._ieee,
                self._attr_id,
                self._attr_name_id,
                switch_name,
            )
        except Exception:
            _LOGGER.exception(
                "relay name auto-sync failed: relay=%s switch=%s reason=%s name=%s",
                self._attr_name_id,
                self._switch_entity_id,
                reason,
                switch_name,
            )
            return

        self._last_synced_switch_name = switch_name
        _LOGGER.debug(
            "relay name auto-sync: relay=%s switch=%s reason=%s name=%s",
            self._attr_name_id,
            self._switch_entity_id,
            reason,
            switch_name,
        )


async def _async_write_relay_name(
    hass: HomeAssistant,
    ieee: str,
    attr_id: int,
    attr_name_id: str,
    value: str,
) -> None:
    """Write a relay label using the raw Tuya DP command format."""
    dp_id = attr_id - 0xEF00
    domain_data = hass.data.setdefault(DOMAIN, {})
    tsn = domain_data.setdefault("tsn", 0)
    tsn = (tsn + 1) % 256
    domain_data["tsn"] = tsn

    cmd = TuyaCommand()
    cmd.status = t.uint8_t(0)
    cmd.tsn = t.uint8_t(tsn)

    datapoint = TuyaDatapointData()
    datapoint.dp = t.uint8_t(dp_id)
    datapoint.data = _build_relay_name_data(value)
    cmd.datapoints = [datapoint]

    _LOGGER.debug(
        "relay name payload: attr=%s input=%s dp=%s tsn=%s encoding=%s raw=%s cmd=%s",
        attr_name_id,
        value,
        dp_id,
        tsn,
        RELAY_NAME_ENCODING,
        datapoint.data.raw.hex(),
        cmd.serialize().hex(),
    )

    await hass.services.async_call(
        ZHA_DOMAIN,
        "issue_zigbee_cluster_command",
        {
            "ieee": ieee,
            "endpoint_id": TUYA_ENDPOINT_ID,
            "cluster_id": TUYA_CLUSTER_ID,
            "cluster_type": TUYA_CLUSTER_TYPE,
            "command_type": "server",
            "command": 0x00,
            "params": {"data": cmd},
        },
        blocking=True,
    )


def _extract_zha_ieee(device: dr.DeviceEntry) -> str | None:
    """Return the ZHA IEEE identifier from a device registry entry."""
    for domain, identifier in device.identifiers:
        if domain == ZHA_DOMAIN:
            return str(identifier)
    return None


def _find_switch_entity_id(hass: HomeAssistant, ieee: str, relay_index: int) -> str | None:
    """Find the matching ZHA switch entity for a relay index on the same device."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    target_identifiers = {(ZHA_DOMAIN, ieee)}

    device_id: str | None = None
    for device in device_registry.devices.values():
        if target_identifiers.issubset(device.identifiers):
            device_id = device.id
            break

    if device_id is None:
        return None

    switch_entries = [
        entry
        for entry in er.async_entries_for_device(entity_registry, device_id)
        if entry.domain == "switch" and not entry.disabled_by
    ]

    if not switch_entries:
        return None

    indexed_entries: dict[int, er.RegistryEntry] = {}
    fallback_entries: list[er.RegistryEntry] = []

    for entry in switch_entries:
        index = _extract_relay_index_from_entity_entry(entry)
        if index is None:
            fallback_entries.append(entry)
            continue
        indexed_entries[index] = entry

    if relay_index in indexed_entries:
        return indexed_entries[relay_index].entity_id

    fallback_entries.sort(key=lambda entry: entry.entity_id)
    if len(fallback_entries) >= relay_index:
        return fallback_entries[relay_index - 1].entity_id

    ordered_entries = sorted(switch_entries, key=lambda entry: entry.entity_id)
    if len(ordered_entries) >= relay_index:
        return ordered_entries[relay_index - 1].entity_id

    return None


def _extract_relay_index_from_entity_entry(entry: er.RegistryEntry) -> int | None:
    """Infer relay index from the entity registry entry fields."""
    for candidate in (
        entry.original_name,
        entry.name,
        entry.entity_id,
        entry.unique_id,
    ):
        if not candidate:
            continue
        match = _RELAY_INDEX_RE.search(str(candidate))
        if match:
            return int(match.group(1))
    return None


def _build_relay_name_data(value: str) -> TuyaData:
    """Build relay-name datapoint payload with a selectable encoding mode."""
    if RELAY_NAME_ENCODING == "string":
        encoded = "".join(f"{ord(ch):04X}" for ch in value)
        return TuyaData(encoded, function=t.uint8_t(0))

    if RELAY_NAME_ENCODING == "raw_utf8":
        raw = value.encode("utf-8")
    elif RELAY_NAME_ENCODING == "raw_utf16be":
        raw = value.encode("utf-16-be")
    elif RELAY_NAME_ENCODING == "raw_utf16le":
        raw = value.encode("utf-16-le")
    else:
        raise ValueError(f"Unsupported relay name encoding: {RELAY_NAME_ENCODING}")

    data = TuyaData(function=t.uint8_t(0))
    data.dp_type = TuyaDPType.RAW
    data.raw = raw
    return data
