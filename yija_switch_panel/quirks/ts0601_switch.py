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
