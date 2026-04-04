"""Yija Switch panel custom integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, INTEGRATION_NAME
from .deploy import async_deploy_quirks
from .sync import async_setup_manager, async_unload_manager
from .weather_manager import async_setup_weather_manager, async_unload_weather_manager
from .weather_runtime import set_runtime_hass

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration domain so runtime helpers always have hass.data."""
    hass.data.setdefault(DOMAIN, {})
    set_runtime_hass(hass)
    _LOGGER.warning("yija_switch_panel async_setup called; domain initialized")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yija Switch panel from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    set_runtime_hass(hass)
    if entry.title != INTEGRATION_NAME:
        hass.config_entries.async_update_entry(entry, title=INTEGRATION_NAME)
    _LOGGER.warning("yija_switch_panel async_setup_entry start entry=%s", entry.entry_id)
    await async_deploy_quirks(hass)
    await async_setup_manager(hass, entry)
    await async_setup_weather_manager(hass, entry)
    _LOGGER.warning("yija_switch_panel async_setup_entry done entry=%s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.warning("yija_switch_panel async_unload_entry start entry=%s", entry.entry_id)
    await async_unload_manager(hass, entry)
    await async_unload_weather_manager(hass, entry)
    if not hass.data.get(DOMAIN, {}).get("weather_entry_ids"):
        set_runtime_hass(None)
    _LOGGER.warning("yija_switch_panel async_unload_entry done entry=%s", entry.entry_id)
    return True
