from dataclasses import dataclass
from enum import Enum

GET_PREFIX = "get_"
SET_PREFIX = ("set_", "change_")


class CacheableAttribute(str, Enum):
    sound_volume = "sound_volume"
    camera_status = "camera_status"
    carpet_clean_mode = "carpet_clean_mode"
    carpet_mode = "carpet_mode"
    child_lock_status = "child_lock_status"
    collision_avoid_status = "collision_avoid_status"
    customize_clean_mode = "customize_clean_mode"
    custom_mode = "custom_mode"
    dnd_timer = "dnd_timer"
    dust_collection_mode = "dust_collection_mode"
    flow_led_status = "flow_led_status"
    identify_furniture_status = "identify_furniture_status"
    identify_ground_material_status = "identify_ground_material_status"
    led_status = "led_status"
    server_timer = "server_timer"
    smart_wash_params = "smart_wash_params"
    timezone = "timezone"
    valley_electricity_timer = "valley_electricity_timer"
    wash_towel_mode = "wash_towel_mode"


class CommandType(Enum):
    GET = 0
    SET = 1


@dataclass
class ParserCommand:
    type: CommandType
    attribute: CacheableAttribute


def parse_method(method: str):
    if method is not None:
        attribute = method.lower()
        if attribute.startswith(GET_PREFIX):
            attribute = attribute.removeprefix(GET_PREFIX)
        elif attribute.startswith(SET_PREFIX):
            for prefix in SET_PREFIX:
                attribute = attribute.removeprefix(prefix)
        try:
            cacheable_attribute = CacheableAttribute(attribute)
            return ParserCommand(type=CommandType.SET, attribute=cacheable_attribute)
        except ValueError:
            pass
    return None
