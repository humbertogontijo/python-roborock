from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

GET_PREFIX = "get_"
SET_PREFIX = ("set_", "change_", "close_")


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


EVICT_TIME = 60


class AttributeCache:
    _value: dict | None = None
    last_update: float | None = None

    def __init__(self, attribute: str):
        self.attribute = attribute

    @property
    def value(self):
        if self.last_update is None or time.monotonic() - self.last_update > EVICT_TIME:
            self._value = None
        return self._value

    def load(self, value: dict):
        self._value = value
        self.last_update = time.monotonic()
        return self._value

    def evict(self):
        self._value = None


class CommandType(Enum):
    OTHER = -1
    GET = 0
    SET = 1


@dataclass
class ParserCommand:
    type: CommandType
    attribute: CacheableAttribute


def parse_method(method: str):
    if method is not None:
        attribute = method.lower()
        command_type = CommandType.OTHER
        if attribute.startswith(GET_PREFIX):
            attribute = attribute.removeprefix(GET_PREFIX)
            command_type = CommandType.GET
        elif attribute.startswith(SET_PREFIX):
            for prefix in SET_PREFIX:
                attribute = attribute.removeprefix(prefix)
            command_type = CommandType.SET
        try:
            cacheable_attribute = CacheableAttribute(attribute)
            return ParserCommand(type=command_type, attribute=cacheable_attribute)
        except ValueError:
            pass
    return None
