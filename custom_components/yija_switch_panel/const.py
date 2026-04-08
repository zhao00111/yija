"""Constants for the Yija Switch panel integration."""

DOMAIN = "yija_switch_panel"
INTEGRATION_NAME = "Yija Switch panel"
ZHA_DOMAIN = "zha"
QUIRKS_DIR = "custom_quirks"
MANAGED_QUIRK_FILES = (
    "ts0601_switch.py",
    "ts0601_switch_screen.py",
)

TARGET_MANUFACTURERS = {"_TZE284_atuj3i0w", "_TZE284_iwyqtclw", "_TZE284_ue6veoat", "_TZE284_vluc293a", "_TZE284_dqwis3rw", "_TZE284_a8wey4go"}
TARGET_MODEL = "TS0601"

F3PRO_MANUFACTURERS = {"_TZE284_7zazvlyn", "_TZE284_idn2htgu"}

TUYA_CLUSTER_ID = 61184
TUYA_CLUSTER_TYPE = "in"
TUYA_ENDPOINT_ID = 1

RELAY_ATTRS = {
    1: 0xEF67,
    2: 0xEF68,
    3: 0xEF69,
    4: 0xEF6A,
}

RELAY_ATTR_NAMES = {
    1: "relay_status_1",
    2: "relay_status_2",
    3: "relay_status_3",
    4: "relay_status_4",
}

SCAN_INTERVAL_SECONDS = 30
MAX_TEXT_LENGTH = 32

# Test encoding used for relay-name datapoints.
# Options:
# - "string": Tuya STRING (type 0x03) carrying Unicode code points as uppercase hex
# - "raw_utf8": Tuya RAW (type 0x00) with UTF-8 bytes
# - "raw_utf16be": Tuya RAW (type 0x00) with UTF-16 big-endian bytes
# - "raw_utf16le": Tuya RAW (type 0x00) with UTF-16 little-endian bytes
RELAY_NAME_ENCODING = "string"

WEATHER_REFRESH_INTERVAL_SECONDS = 300

CONF_WEATHER_ENTITY_ID = "weather_entity_id"
DEFAULT_WEATHER_ENTITY_ID = ""
