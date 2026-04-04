"""Runtime helpers for Tuya weather request/response handling."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .weather_manager import CurrentWeather

_LOGGER = logging.getLogger(__name__)

REQUEST_CMD_ID = 0x60
RESPONSE_CMD_ID = 0x61

WEATHER_ID_TEMPERATURE = 0x01
WEATHER_ID_HUMIDITY = 0x02
WEATHER_ID_CONDITION = 0x03
FORECAST_ID = 0x12
REALTIME_ID = 0x13

_RUNTIME_HASS: HomeAssistant | None = None


def set_runtime_hass(hass: HomeAssistant | None) -> None:
    """Persist Home Assistant instance for quirk/runtime access."""
    global _RUNTIME_HASS
    _RUNTIME_HASS = hass
    if hass is None:
        _LOGGER.warning("weather runtime: runtime hass cleared")
    else:
        _LOGGER.warning("weather runtime: runtime hass registered id=%s", id(hass))


def get_current_weather(hass: HomeAssistant | None) -> CurrentWeather:
    """Get current weather or return a safe default."""
    effective_hass = hass or _RUNTIME_HASS

    if effective_hass is None:
        _LOGGER.warning("weather runtime: hass is None, using default cloudy 16°C")
        return CurrentWeather()

    manager = effective_hass.data.get(DOMAIN, {}).get("weather_manager")
    if manager is None:
        _LOGGER.warning("weather runtime: weather_manager missing in hass.data, using default cloudy 16°C")
        return CurrentWeather()

    try:
        weather = manager.get_current_weather()
        _LOGGER.warning(
            "weather runtime: resolved weather source=%s entity=%s temp=%s humidity=%s cond=%s",
            weather.source,
            weather.entity_id,
            weather.temperature_c,
            weather.humidity,
            weather.condition_code,
        )
        return weather
    except Exception:
        _LOGGER.exception("weather runtime: failed to read weather; using default cloudy 16°C")
        return CurrentWeather()


def build_weather_response(request_raw: bytes, weather: CurrentWeather) -> bytes:
    """Build a minimal 0x61 response for current temp + condition."""
    seq_prefix, weather_request = _split_weather_request(request_raw)
    version = weather_request[0] if len(weather_request) >= 1 else 0x11
    location_type = weather_request[1] if len(weather_request) >= 2 else 0x00

    requested_ids = _extract_requested_weather_ids(weather_request)
    if not requested_ids:
        requested_ids = [WEATHER_ID_TEMPERATURE, WEATHER_ID_HUMIDITY, WEATHER_ID_CONDITION]
        _LOGGER.warning("weather runtime: request did not include supported IDs, defaulting to ids=%s raw=%s", requested_ids, request_raw.hex())
    else:
        _LOGGER.warning("weather runtime: extracted requested_ids=%s from raw=%s", requested_ids, request_raw.hex())

    forecast_days, realtime_flag = _parse_controls(weather_request)
    payload = bytearray(seq_prefix)
    payload.extend([FORECAST_ID, forecast_days, REALTIME_ID, realtime_flag])

    for weather_id in requested_ids:
        if weather_id == WEATHER_ID_TEMPERATURE:
            payload.append(WEATHER_ID_TEMPERATURE)
            temp_bytes = _encode_int16(weather.temperature_c)
            payload.extend(temp_bytes)
            for _ in range(forecast_days):
                payload.extend(temp_bytes)
            _LOGGER.warning(
                "weather runtime: appended temperature id=0x01 value=%s bytes=%s forecast_days=%s realtime=%s",
                weather.temperature_c,
                temp_bytes.hex(),
                forecast_days,
                realtime_flag,
            )
        elif weather_id == WEATHER_ID_HUMIDITY:
            payload.append(WEATHER_ID_HUMIDITY)
            humidity_bytes = _fixed_humidity_bytes(forecast_days)
            payload.extend(humidity_bytes)
            _LOGGER.warning(
                "weather runtime: appended humidity id=0x02 value=%s bytes=%s forecast_days=%s realtime=%s",
                weather.humidity,
                humidity_bytes.hex(),
                forecast_days,
                realtime_flag,
            )
        elif weather_id == WEATHER_ID_CONDITION:
            payload.append(WEATHER_ID_CONDITION)
            condition_bytes = _encode_uint8(weather.condition_code)
            payload.extend(condition_bytes)
            for _ in range(forecast_days):
                payload.extend(condition_bytes)
            _LOGGER.warning(
                "weather runtime: appended condition id=0x03 value=%s bytes=%s forecast_days=%s realtime=%s",
                weather.condition_code,
                condition_bytes.hex(),
                forecast_days,
                realtime_flag,
            )
        else:
            _LOGGER.warning("weather runtime: unsupported weather_id=%s ignored", weather_id)

    response = bytes(payload)
    _LOGGER.warning(
        "weather runtime: built response seq=%s version=0x%02x location=0x%02x forecast_days=%s realtime=%s payload=%s",
        seq_prefix.hex() if seq_prefix else "none",
        version,
        location_type,
        forecast_days,
        realtime_flag,
        response.hex(),
    )
    return response


def _extract_requested_weather_ids(request_raw: bytes) -> list[int]:
    """Extract requested weather IDs from a 0x60 request."""
    if len(request_raw) <= 2:
        _LOGGER.warning("weather runtime: request too short to parse ids raw=%s", request_raw.hex())
        return []

    ids: list[int] = []
    for value in request_raw[2:]:
        if value in (FORECAST_ID, REALTIME_ID):
            _LOGGER.warning("weather runtime: reached control marker 0x%02x while parsing ids raw=%s", value, request_raw.hex())
            break
        if value in (WEATHER_ID_TEMPERATURE, WEATHER_ID_HUMIDITY, WEATHER_ID_CONDITION) and value not in ids:
            ids.append(value)
        else:
            _LOGGER.warning("weather runtime: encountered unsupported or duplicate requested id=0x%02x raw=%s", value, request_raw.hex())
    return ids


def _parse_controls(request_raw: bytes) -> tuple[int, int]:
    """Parse forecast_days and realtime_flag from a 0x60 request."""
    forecast_days = 0
    realtime_flag = 1

    for idx, value in enumerate(request_raw):
        if value == FORECAST_ID and idx + 1 < len(request_raw):
            try:
                forecast_days = max(0, min(7, int(request_raw[idx + 1])))
            except Exception:
                forecast_days = 0
        if value == REALTIME_ID and idx + 1 < len(request_raw):
            try:
                realtime_flag = 1 if int(request_raw[idx + 1]) else 0
            except Exception:
                realtime_flag = 1

    _LOGGER.warning(
        "weather runtime: parsed controls forecast_days=%s realtime_flag=%s raw=%s",
        forecast_days,
        realtime_flag,
        request_raw.hex(),
    )
    return forecast_days, realtime_flag


def _encode_int16(value: int) -> bytes:
    signed = int(value) & 0xFFFF
    return bytes([(signed >> 8) & 0xFF, signed & 0xFF])


def _encode_uint8(value: int) -> bytes:
    """Encode Tuya conditionNum as a single uint8 byte."""
    return bytes([int(value) & 0xFF])


def _fixed_humidity_bytes(forecast_days: int) -> bytes:
    """Return fixed humidity bytes."""
    return bytes.fromhex("0045003E00490055")


def _split_weather_request(request_raw: bytes) -> tuple[bytes, bytes]:
    """Split EF00 weather request into 2-byte sequence prefix and protocol payload."""
    if len(request_raw) >= 4 and request_raw[2] == 0x11 and request_raw[3] in (0x00, 0x01):
        return request_raw[:2], request_raw[2:]
    return b"", request_raw
