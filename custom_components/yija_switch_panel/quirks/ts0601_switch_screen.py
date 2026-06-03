SCENE_COUNT_BY_MANUFACTURER = {
    "_TZE284_atuj3i0w": 4,
    "_TZE284_bvnpuyqo": 4,
    "_TZE284_iwyqtclw": 4,
    "_TZE284_ue6veoat": 4,
    "_TZE284_vluc293a": 3,
    "_TZE284_dqwis3rw": 2,
    "_TZE284_a8wey4go": 1,
    "_TZE284_yrwmnya3": 8,
    "_TZE284_gapj4ghu": 6,
}

F3PRO_MANUFACTURERS = ("_TZE284_7zazvlyn", "_TZE284_idn2htgu")


def _switch_count_for_manufacturer(manufacturer: str) -> int:
    return min(SCENE_COUNT_BY_MANUFACTURER[manufacturer], 4)


MANUFACTURERS_WITHOUT_DISPLAY_OPTIONS = {
    "_TZE284_bvnpuyqo",
    "_TZE284_vluc293a",
    "_TZE284_dqwis3rw",
    "_TZE284_a8wey4go",
    "_TZE284_yrwmnya3",
    "_TZE284_gapj4ghu",
}


import logging
from datetime import UTC, datetime, timedelta, timezone

import zigpy.types as t

from zhaquirks import LocalDataCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster

from custom_components.yija_switch_panel.weather_runtime import (
    REQUEST_CMD_ID,
    RESPONSE_CMD_ID,
    build_weather_response,
    get_current_weather,
)
from zigpy.zcl.clusters.general import Basic, Time
from zigpy.zcl import foundation
from zigpy.quirks.v2 import ClusterType, EntityType


# Tuya manufacturer cluster attribute ids generated from DP 103-106:
# 103 -> 0xEF67 (61287)
# 104 -> 0xEF68 (61288)
# 105 -> 0xEF69 (61289)
# 106 -> 0xEF6A (61290)

HKT = timezone(timedelta(hours=8))
ZIGBEE_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)
_LOGGER = logging.getLogger(__name__)


def _resolve_hass_from_device(device):
    """Best-effort resolve Home Assistant instance from zigpy/ZHA device."""
    app = getattr(device, "application", None)
    if app is None:
        return None

    for attr in ("hass", "_hass"):
        hass = getattr(app, attr, None)
        if hass is not None:
            return hass

    for attr in ("_gateway", "gateway", "_application", "application_controller", "controller"):
        obj = getattr(app, attr, None)
        if obj is None:
            continue
        for hass_attr in ("hass", "_hass"):
            hass = getattr(obj, hass_attr, None)
            if hass is not None:
                return hass

    return None



def now_string(_value):
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PowerOnState(t.enum8):
    OFF = 0
    ON = 1
    LAST_STATE = 2


class ModeType(t.enum8):
    SWITCH_1 = 0
    SCENE_1 = 1


class LightMode(t.enum8):
    RELAY = 0
    POS = 1
    NONE = 2


class F3ProPanelMode(t.enum8):
    SWITCH = 0
    DIMMER = 1
    CURTAIN = 2


class CurtainControl(t.enum8):
    OPEN = 0
    STOP = 1
    CLOSE = 2


class SceneTimeCluster(LocalDataCluster):
    cluster_id = 0xFC00
    ep_attribute = "scene_time"
    attributes = {
        0x0000: ("last_triggered", t.CharacterString, True),
    }


class TuyaScreenBasicCluster(Basic):
    """Basic cluster with extra logging for Tuya screen status reports."""

    def _update_attribute(self, attrid: int, value) -> None:
        if attrid in {0xFFDF, 0xFFE2, 0xFFE4}:
            _LOGGER.warning(
                "screen basic status report: device=%s nwk=0x%04x attr=0x%04X raw=%r",
                self.endpoint.device.ieee,
                self.endpoint.device.nwk,
                attrid,
                value,
            )
        super()._update_attribute(attrid, value)


class TuyaHongKongTimeCluster(Time):
    """Return a fixed UTC+8 time view for devices that mis-handle local_time."""

    def handle_read_attribute_time(self) -> t.UTCTime:
        now_utc = datetime.now(UTC)
        return t.UTCTime(int((now_utc - ZIGBEE_EPOCH).total_seconds()))

    def handle_read_attribute_time_zone(self) -> t.int32s:
        return t.int32s(int(HKT.utcoffset(None).total_seconds()))

    def handle_read_attribute_standard_time(self) -> t.StandardTime:
        now_hkt = datetime.now(HKT)
        utc_seconds = int((now_hkt.astimezone(UTC) - ZIGBEE_EPOCH).total_seconds())
        return t.StandardTime(utc_seconds + int(HKT.utcoffset(None).total_seconds()))

    def handle_read_attribute_local_time(self) -> t.LocalTime:
        now_hkt = datetime.now(HKT)
        utc_seconds = int((now_hkt.astimezone(UTC) - ZIGBEE_EPOCH).total_seconds())
        return t.LocalTime(utc_seconds + int(HKT.utcoffset(None).total_seconds()))


class TuyaScreenMCUCluster(TuyaMCUCluster):
    """MCU cluster with explicit time-sync logging for this screen switch."""

    class ServerCommandDefs(TuyaMCUCluster.ServerCommandDefs):
        """Server command definitions."""

        weather_data = foundation.ZCLCommandDef(
            id=RESPONSE_CMD_ID,
            schema={"data": t.Bytes},
            manufacturer_code=None,
        )

    class ClientCommandDefs(TuyaMCUCluster.ClientCommandDefs):
        """Client command definitions."""

        weather_request = foundation.ZCLCommandDef(
            id=REQUEST_CMD_ID,
            schema={"data": t.Bytes},
            manufacturer_code=None,
        )
    def _build_weather_payload(self, request_raw: bytes) -> bytes:
        """Build a minimal weather payload from Home Assistant weather."""
        hass = _resolve_hass_from_device(self.endpoint.device)
        if hass is None:
            _LOGGER.warning(
                "screen weather payload: hass unavailable for device=%s nwk=0x%04x, using default weather",
                self.endpoint.device.ieee,
                self.endpoint.device.nwk,
            )

        weather = get_current_weather(hass)
        payload = build_weather_response(request_raw, weather)
        _LOGGER.warning(
            "screen weather response built: device=%s source=%s entity=%s temp=%s cond=%s request=%s response=%s",
            self.endpoint.device.ieee,
            weather.source,
            weather.entity_id,
            weather.temperature_c,
            weather.condition_code,
            request_raw.hex(),
            payload.hex(),
        )
        return payload

    def handle_set_time_request(self, payload: t.uint16_t) -> foundation.Status:
        _LOGGER.warning(
            "screen set_time_request received: payload=%s device=%s nwk=0x%04x",
            payload,
            self.endpoint.device.ieee,
            self.endpoint.device.nwk,
        )
        return super().handle_set_time_request(payload)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list,
        *,
        dst_addressing=None,
    ) -> None:
        """Capture vendor-specific screen commands before generic Tuya handling."""
        _LOGGER.warning(
            "screen cluster request: device=%s nwk=0x%04x cmd=0x%02x tsn=%s args_count=%s disable_default_response=%s",
            self.endpoint.device.ieee,
            self.endpoint.device.nwk,
            hdr.command_id,
            hdr.tsn,
            len(args),
            hdr.frame_control.disable_default_response,
        )
        if hdr.command_id == REQUEST_CMD_ID:
            if len(args) == 1 and isinstance(args[0], (bytes, bytearray, t.Bytes)):
                request_raw = bytes(args[0])
            else:
                request_raw = bytes(
                    int(arg) & 0xFF if isinstance(arg, int) else bytes(arg)[0]
                    for arg in args
                )
            payload_parts = []
            for idx, arg in enumerate(args):
                payload_parts.append(
                    {
                        "index": idx,
                        "type": type(arg).__name__,
                        "repr": repr(arg),
                        "hex": (
                            f"{int(arg) & 0xFF:02x}"
                            if isinstance(arg, int)
                            else bytes(arg).hex()
                        ),
                    }
                )
            response_payload = self._build_weather_payload(request_raw)
            _LOGGER.warning(
                "screen weather-like command received: device=%s nwk=0x%04x cmd=0x60 raw=%s args=%s response=%s",
                self.endpoint.device.ieee,
                self.endpoint.device.nwk,
                request_raw.hex(),
                payload_parts,
                response_payload.hex(),
            )
            if not hdr.frame_control.disable_default_response:
                # Zigbee default response acts like the UART-side request ACK.
                self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)
            self.create_catching_task(
                super().reply(
                    False,
                    RESPONSE_CMD_ID,
                    self.ServerCommandDefs.weather_data.schema,
                    data=t.Bytes(response_payload),
                    tsn=hdr.tsn,
                    expect_reply=False,
                )
            )
            return

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


def _register_screen_quirk(manufacturer: str) -> None:
    scene_count = SCENE_COUNT_BY_MANUFACTURER[manufacturer]
    switch_count = _switch_count_for_manufacturer(manufacturer)
    has_display_options = manufacturer not in MANUFACTURERS_WITHOUT_DISPLAY_OPTIONS
    builder = (
        TuyaQuirkBuilder(manufacturer, "TS0601")
        .tuya_enchantment(data_query_spell=True)
        .replaces(TuyaScreenBasicCluster, endpoint_id=1)
        .replaces(TuyaHongKongTimeCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    )

    for scene_index in range(1, scene_count + 1):
        endpoint_id = 40 + scene_index
        builder = (
            builder.adds_endpoint(endpoint_id, device_type=0x0051)
            .adds(SceneTimeCluster, endpoint_id=endpoint_id)
            .sensor(
                attribute_name="last_triggered",
                cluster_id=SceneTimeCluster.cluster_id,
                endpoint_id=endpoint_id,
                translation_key=f"scene_{scene_index}_last_triggered",
                fallback_name=f"Scene {scene_index} Last Triggered",
                entity_type=EntityType.DIAGNOSTIC,
                attribute_initialized_from_cache=False,
            )
            .tuya_dp(
                dp_id=scene_index,
                ep_attribute=SceneTimeCluster.ep_attribute,
                attribute_name="last_triggered",
                endpoint_id=endpoint_id,
                converter=now_string,
            )
        )

    for switch_index in range(1, switch_count + 1):
        builder = (
            builder.tuya_switch(
                dp_id=23 + switch_index,
                attribute_name=f"switch_{switch_index}",
                translation_key=f"switch_{switch_index}",
                fallback_name=f"Switch {switch_index}",
                entity_type=EntityType.STANDARD,
            )
            .tuya_enum(
                dp_id=38 + switch_index,
                attribute_name=f"power_on_state_{switch_index}",
                enum_class=PowerOnState,
                translation_key=f"power_on_state_{switch_index}",
                fallback_name=f"Power On State {switch_index}",
                entity_type=EntityType.CONFIG,
            )
            .tuya_enum(
                dp_id=17 + switch_index,
                attribute_name=f"mode_{switch_index}",
                enum_class=ModeType,
                translation_key=f"mode_{switch_index}",
                fallback_name=f"Mode {switch_index}",
                entity_type=EntityType.CONFIG,
            )
            .tuya_dp_attribute(
                dp_id=102 + switch_index,
                attribute_name=f"relay_status_{switch_index}",
                type=t.CharacterString,
                access=foundation.ZCLAttributeAccess.Read
                | foundation.ZCLAttributeAccess.Write,
            )
        )

    builder = builder.tuya_switch(
        dp_id=101,
        attribute_name="backlight",
        translation_key="backlight",
        fallback_name="Backlight",
        entity_type=EntityType.CONFIG,
    )

    if has_display_options:
        builder = (
            builder.tuya_switch(
                dp_id=36,
                attribute_name="backlight_screen",
                translation_key="time_display",
                fallback_name="Time Display",
                entity_type=EntityType.CONFIG,
            )
            .tuya_enum(
                dp_id=37,
                attribute_name="light_mode",
                enum_class=LightMode,
                translation_key="light_mode",
                fallback_name="Light Mode",
                entity_type=EntityType.CONFIG,
            )
        )

    (
        builder.skip_configuration().add_to_registry(
            replacement_cluster=TuyaScreenMCUCluster
        )
    )


for _manufacturer in SCENE_COUNT_BY_MANUFACTURER:
    _register_screen_quirk(_manufacturer)



def _register_f3pro_screen_quirk(manufacturer: str) -> None:
    builder = (
        TuyaQuirkBuilder(manufacturer, "TS0601")
        .tuya_enchantment(data_query_spell=True)
        .replaces(TuyaScreenBasicCluster, endpoint_id=1)
        .replaces(TuyaHongKongTimeCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    )

    for scene_index in range(1, 9):
        endpoint_id = 40 + scene_index
        builder = (
            builder.adds_endpoint(endpoint_id, device_type=0x0051)
            .adds(SceneTimeCluster, endpoint_id=endpoint_id)
            .sensor(
                attribute_name="last_triggered",
                cluster_id=SceneTimeCluster.cluster_id,
                endpoint_id=endpoint_id,
                translation_key=f"scene_{scene_index}_last_triggered",
                fallback_name=f"Scene {scene_index} Last Triggered",
                entity_type=EntityType.DIAGNOSTIC,
                attribute_initialized_from_cache=False,
            )
            .tuya_dp(
                dp_id=scene_index,
                ep_attribute=SceneTimeCluster.ep_attribute,
                attribute_name="last_triggered",
                endpoint_id=endpoint_id,
                converter=now_string,
            )
        )

    for switch_index, dp_id in enumerate(range(121, 125), start=1):
        builder = builder.tuya_switch(
            dp_id=dp_id,
            attribute_name=f"switch_{switch_index}",
            translation_key=f"switch_{switch_index}",
            fallback_name=f"Switch {switch_index}",
            entity_type=EntityType.STANDARD,
        )

    builder = (
        builder.tuya_enum(
            dp_id=106,
            attribute_name="power_on_state",
            enum_class=PowerOnState,
            translation_key="power_on_state",
            fallback_name="Power On State",
            entity_type=EntityType.CONFIG,
        )
        .tuya_switch(
            dp_id=149,
            attribute_name="backlight",
            translation_key="backlight",
            fallback_name="Backlight",
            entity_type=EntityType.CONFIG,
        )
        .tuya_enum(
            dp_id=150,
            attribute_name="panel_mode",
            enum_class=F3ProPanelMode,
            translation_key="panel_mode",
            fallback_name="Panel Mode",
            entity_type=EntityType.CONFIG,
        )
        .tuya_number(
            dp_id=104,
            type=t.uint32_t,
            attribute_name="countdown_1",
            min_value=0,
            max_value=86400,
            step=1,
            unit="s",
            translation_key="countdown_1",
            fallback_name="Countdown 1",
            entity_type=EntityType.CONFIG,
            initially_disabled=True,
        )
    )

    for group_index, (switch_dp, bright_dp, warm_dp) in enumerate(
        ((117, 102, 109), (118, 103, 110), (119, 105, 111), (120, 107, 112)),
        start=1,
    ):
        builder = (
            builder.tuya_switch(
                dp_id=switch_dp,
                attribute_name=f"light_group_{group_index}_power",
                translation_key=f"light_group_{group_index}_power",
                fallback_name=f"Light Group {group_index} Power",
                entity_type=EntityType.STANDARD,
                initially_disabled=False,
            )
            .tuya_number(
                dp_id=bright_dp,
                type=t.uint8_t,
                attribute_name=f"light_group_{group_index}_brightness",
                min_value=1,
                max_value=100,
                step=1,
                unit="%",
                translation_key=f"light_group_{group_index}_brightness",
                fallback_name=f"Light Group {group_index} Brightness",
                entity_type=EntityType.STANDARD,
                initially_disabled=False,
            )
            .tuya_number(
                dp_id=warm_dp,
                type=t.uint8_t,
                attribute_name=f"light_group_{group_index}_color_temp",
                min_value=1,
                max_value=100,
                step=1,
                unit="%",
                translation_key=f"light_group_{group_index}_color_temp",
                fallback_name=f"Light Group {group_index} Color Temp",
                entity_type=EntityType.STANDARD,
                initially_disabled=False,
            )
        )

    for group_index, (position_dp, control_dp) in enumerate(
        ((113, 133), (114, 134), (115, 135), (116, 136)), start=1
    ):
        builder = (
            builder.tuya_number(
                dp_id=position_dp,
                type=t.uint8_t,
                attribute_name=f"curtain_group_{group_index}_position",
                min_value=1,
                max_value=100,
                step=1,
                unit="%",
                translation_key=f"curtain_group_{group_index}_position",
                fallback_name=f"Curtain Group {group_index} Position",
                entity_type=EntityType.STANDARD,
                initially_disabled=False,
            )
            .tuya_enum(
                dp_id=control_dp,
                attribute_name=f"curtain_group_{group_index}_control",
                enum_class=CurtainControl,
                translation_key=f"curtain_group_{group_index}_control",
                fallback_name=f"Curtain Group {group_index} Control",
                entity_type=EntityType.STANDARD,
                initially_disabled=False,
            )
        )

    (
        builder.skip_configuration().add_to_registry(
            replacement_cluster=TuyaScreenMCUCluster
        )
    )


for _manufacturer in F3PRO_MANUFACTURERS:
    _register_f3pro_screen_quirk(_manufacturer)
