from datetime import datetime

import zigpy.types as t

from zhaquirks import LocalDataCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zigpy.quirks.v2 import EntityType


def now_string(_value):
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PowerOnState(t.enum8):
    OFF = 0
    ON = 1
    LAST_STATE = 2


class ModeType(t.enum8):
    SWITCH_1 = 0
    SCENE_1 = 1


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


def _register_switch_quirk(manufacturer: str) -> None:
    scene_count = SCENE_COUNT_BY_MANUFACTURER[manufacturer]
    switch_count = _switch_count_for_manufacturer(manufacturer)
    builder = TuyaQuirkBuilder(manufacturer, "TS0601").tuya_enchantment(
        data_query_spell=True
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
        )

    (
        builder.tuya_switch(
            dp_id=101,
            attribute_name="backlight",
            translation_key="backlight",
            fallback_name="Backlight",
            entity_type=EntityType.CONFIG,
        )
        .skip_configuration()
        .add_to_registry()
    )


for _manufacturer in SCENE_COUNT_BY_MANUFACTURER:
    _register_switch_quirk(_manufacturer)



def _register_f3pro_quirk(manufacturer: str) -> None:
    builder = TuyaQuirkBuilder(manufacturer, "TS0601").tuya_enchantment(
        data_query_spell=True
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
                fallback_name=f"Light Group {group_index}",
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
                fallback_name=f"Curtain Group {group_index}",
                entity_type=EntityType.STANDARD,
                initially_disabled=False,
            )
        )

    (
        builder.skip_configuration().add_to_registry()
    )


for _manufacturer in F3PRO_MANUFACTURERS:
    _register_f3pro_quirk(_manufacturer)
