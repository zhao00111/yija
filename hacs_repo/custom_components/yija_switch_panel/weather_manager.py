"""Weather source management for Tuya weather responses."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_WEATHER_ENTITY_ID, DEFAULT_WEATHER_ENTITY_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_TEMP_C = 16
DEFAULT_HUMIDITY = 69
DEFAULT_CONDITION_CODE = 142  # 多云

CONDITION_MAP = {
    "sunny": 120,
    "clear-night": 146,
    "partlycloudy": 129,
    "cloudy": 142,
    "fog": 121,
    "hail": 127,
    "lightning": 110,
    "lightning-rainy": 143,
    "pouring": 145,
    "rainy": 112,
    "snowy": 105,
    "snowy-rainy": 113,
    "windy": 142,
    "windy-variant": 142,
    "exceptional": 142,
}


@dataclass(slots=True)
class CurrentWeather:
    """Normalized current weather for the panel."""

    temperature_c: int = DEFAULT_TEMP_C
    humidity: int = DEFAULT_HUMIDITY
    condition_code: int = DEFAULT_CONDITION_CODE
    entity_id: str | None = None
    source: str = "default"


async def async_setup_weather_manager(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register weather access for this integration entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get("weather_manager")
    if manager is None:
        manager = WeatherManager(hass)
        domain_data["weather_manager"] = manager
        _LOGGER.warning("weather_manager created for entry=%s", entry.entry_id)
    manager.set_config_entry(entry)
    domain_data.setdefault("weather_entry_ids", set()).add(entry.entry_id)
    _LOGGER.warning(
        "weather_manager registered entry=%s active_entries=%s configured_weather=%s",
        entry.entry_id,
        sorted(domain_data.get("weather_entry_ids", [])),
        manager.configured_entity_id,
    )


async def async_unload_weather_manager(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unregister weather access when the integration unloads."""
    domain_data = hass.data.get(DOMAIN)
    if not domain_data:
        _LOGGER.warning("weather_manager unload skipped; no domain data for entry=%s", entry.entry_id)
        return

    entry_ids = domain_data.get("weather_entry_ids")
    if isinstance(entry_ids, set):
        entry_ids.discard(entry.entry_id)
        if not entry_ids:
            domain_data.pop("weather_entry_ids", None)
            domain_data.pop("weather_manager", None)


class WeatherManager:
    """Read current weather from Home Assistant with safe defaults.

    Supported configured entities:
    - weather.xxx: reads attributes.temperature and state as condition
    - sensor.xxx: reads state or attributes.temperature as temperature, condition defaults to cloudy
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.configured_entity_id: str = DEFAULT_WEATHER_ENTITY_ID

    def set_config_entry(self, entry: ConfigEntry) -> None:
        self.configured_entity_id = (
            entry.options.get(CONF_WEATHER_ENTITY_ID)
            or entry.data.get(CONF_WEATHER_ENTITY_ID)
            or DEFAULT_WEATHER_ENTITY_ID
        ).strip()

    def get_current_weather(self) -> CurrentWeather:
        entity_id, source = self._pick_weather_entity_id()
        if entity_id is None:
            _LOGGER.warning(
                "weather lookup: no usable weather/sensor entity available, using default temp=%s cond=%s",
                DEFAULT_TEMP_C,
                DEFAULT_CONDITION_CODE,
            )
            return CurrentWeather()

        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("weather lookup: selected entity=%s but current state is missing, using defaults", entity_id)
            return CurrentWeather(entity_id=entity_id, source=source)

        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        attrs = dict(state.attributes)

        try:
            if domain == "weather":
                raw_temp = attrs.get("temperature")
                if raw_temp is None:
                    forecast = attrs.get("forecast") or []
                    if forecast and isinstance(forecast[0], dict):
                        raw_temp = forecast[0].get("temperature")
                temperature_c = DEFAULT_TEMP_C if raw_temp is None else int(round(float(raw_temp)))
                raw_humidity = attrs.get("humidity")
                humidity = DEFAULT_HUMIDITY if raw_humidity is None else max(0, min(100, int(round(float(raw_humidity)))))
                condition_code = CONDITION_MAP.get(state.state, DEFAULT_CONDITION_CODE)
                _LOGGER.warning(
                    "weather lookup: entity=%s source=%s domain=weather state=%s raw_temp=%r raw_humidity=%r mapped_temp=%s mapped_humidity=%s mapped_condition=%s attrs=%s",
                    entity_id,
                    source,
                    state.state,
                    raw_temp,
                    raw_humidity,
                    temperature_c,
                    humidity,
                    condition_code,
                    attrs,
                )
                return CurrentWeather(
                    temperature_c=temperature_c,
                    humidity=humidity,
                    condition_code=condition_code,
                    entity_id=entity_id,
                    source=source,
                )

            if domain == "sensor":
                raw_temp = state.state
                if raw_temp in (None, "", "unknown", "unavailable"):
                    raw_temp = attrs.get("temperature")
                temperature_c = DEFAULT_TEMP_C if raw_temp is None else int(round(float(raw_temp)))
                raw_humidity = attrs.get("humidity")
                humidity = DEFAULT_HUMIDITY if raw_humidity is None else max(0, min(100, int(round(float(raw_humidity)))))
                condition_code = DEFAULT_CONDITION_CODE
                _LOGGER.warning(
                    "weather lookup: entity=%s source=%s domain=sensor state=%s raw_temp=%r raw_humidity=%r mapped_temp=%s mapped_humidity=%s mapped_condition=%s attrs=%s",
                    entity_id,
                    source,
                    state.state,
                    raw_temp,
                    raw_humidity,
                    temperature_c,
                    humidity,
                    condition_code,
                    attrs,
                )
                return CurrentWeather(
                    temperature_c=temperature_c,
                    humidity=humidity,
                    condition_code=condition_code,
                    entity_id=entity_id,
                    source=source,
                )

            _LOGGER.warning(
                "weather lookup: unsupported domain for entity=%s domain=%s using defaults attrs=%s",
                entity_id,
                domain,
                attrs,
            )
            return CurrentWeather(entity_id=entity_id, source=source)

        except (TypeError, ValueError):
            _LOGGER.warning(
                "weather lookup: invalid temperature on entity=%s domain=%s state=%r attrs=%s using default=%s",
                entity_id,
                domain,
                state.state,
                attrs,
                DEFAULT_TEMP_C,
            )
            return CurrentWeather(
                temperature_c=DEFAULT_TEMP_C,
                condition_code=DEFAULT_CONDITION_CODE,
                entity_id=entity_id,
                source=source,
            )

    def _pick_weather_entity_id(self) -> tuple[str | None, str]:
        configured = self.configured_entity_id
        if configured:
            state = self.hass.states.get(configured)
            if state is not None and state.state not in ("unknown", "unavailable"):
                _LOGGER.warning("weather entity pick: using configured entity=%s", configured)
                return configured, "configured"
            _LOGGER.warning(
                "weather entity pick: configured entity=%s unavailable_or_missing state=%s",
                configured,
                None if state is None else state.state,
            )

        preferred = "weather.home"
        state = self.hass.states.get(preferred)
        if state is not None and state.state not in ("unknown", "unavailable"):
            _LOGGER.warning("weather entity pick: using preferred entity=%s", preferred)
            return preferred, "preferred"

        all_weather = [
            st for st in self.hass.states.async_all("weather")
            if st.state not in ("unknown", "unavailable")
        ]
        if all_weather:
            picked = all_weather[0].entity_id
            _LOGGER.warning(
                "weather entity pick: preferred/configured unavailable, using first usable weather entity=%s candidates=%s",
                picked,
                [state.entity_id for state in all_weather],
            )
            return picked, "auto-weather"

        # Fallback to a usable temperature sensor if available.
        sensor_candidates = []
        for st in self.hass.states.async_all("sensor"):
            attrs = st.attributes or {}
            if st.state in ("unknown", "unavailable", "", None):
                continue
            if attrs.get("device_class") == "temperature" or attrs.get("unit_of_measurement") in ("°C", "℃", "°F", "℉"):
                sensor_candidates.append(st)

        if sensor_candidates:
            picked = sensor_candidates[0].entity_id
            _LOGGER.warning(
                "weather entity pick: no usable weather entity, using temperature sensor=%s candidates=%s",
                picked,
                [state.entity_id for state in sensor_candidates],
            )
            return picked, "auto-sensor"

        _LOGGER.warning("weather entity pick: no usable weather/sensor entities found, using default cloudy 16°C")
        return None, "default"
