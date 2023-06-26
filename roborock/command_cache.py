from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional

from roborock import RoborockCommand

GET_PREFIX = "get_"
SET_PREFIX = ("set_", "change_", "close_")


class CacheableAttribute(str, Enum):
    status = "status"
    consumable = "consumable"
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


@dataclass
class RoborockAttribute:
    attribute: str
    get_command: RoborockCommand
    add_command: Optional[RoborockCommand] = None
    set_command: Optional[RoborockCommand] = None
    close_command: Optional[RoborockCommand] = None


def create_cache_map():
    cache_map: Mapping[CacheableAttribute, RoborockAttribute] = {
        CacheableAttribute.status: RoborockAttribute(
            attribute="status",
            get_command=RoborockCommand.GET_STATUS,
        ),
        CacheableAttribute.consumable: RoborockAttribute(
            attribute="consumable",
            get_command=RoborockCommand.GET_CONSUMABLE,
        ),
        CacheableAttribute.sound_volume: RoborockAttribute(
            attribute="sound_volume",
            get_command=RoborockCommand.GET_SOUND_VOLUME,
            set_command=RoborockCommand.CHANGE_SOUND_VOLUME,
        ),
        CacheableAttribute.camera_status: RoborockAttribute(
            attribute="camera_status",
            get_command=RoborockCommand.GET_CAMERA_STATUS,
            set_command=RoborockCommand.SET_CAMERA_STATUS,
        ),
        CacheableAttribute.carpet_clean_mode: RoborockAttribute(
            attribute="carpet_clean_mode",
            get_command=RoborockCommand.GET_CARPET_CLEAN_MODE,
            set_command=RoborockCommand.SET_CARPET_CLEAN_MODE,
        ),
        CacheableAttribute.carpet_mode: RoborockAttribute(
            attribute="carpet_mode",
            get_command=RoborockCommand.GET_CARPET_MODE,
            set_command=RoborockCommand.SET_CARPET_MODE,
        ),
        CacheableAttribute.child_lock_status: RoborockAttribute(
            attribute="child_lock_status",
            get_command=RoborockCommand.GET_CHILD_LOCK_STATUS,
            set_command=RoborockCommand.SET_CHILD_LOCK_STATUS,
        ),
        CacheableAttribute.collision_avoid_status: RoborockAttribute(
            attribute="collision_avoid_status",
            get_command=RoborockCommand.GET_COLLISION_AVOID_STATUS,
            set_command=RoborockCommand.SET_COLLISION_AVOID_STATUS,
        ),
        CacheableAttribute.customize_clean_mode: RoborockAttribute(
            attribute="customize_clean_mode",
            get_command=RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE,
            set_command=RoborockCommand.SET_CUSTOMIZE_CLEAN_MODE,
        ),
        CacheableAttribute.custom_mode: RoborockAttribute(
            attribute="custom_mode",
            get_command=RoborockCommand.GET_CUSTOM_MODE,
            set_command=RoborockCommand.SET_CUSTOM_MODE,
        ),
        CacheableAttribute.dnd_timer: RoborockAttribute(
            attribute="dnd_timer",
            get_command=RoborockCommand.GET_DND_TIMER,
            set_command=RoborockCommand.SET_DND_TIMER,
            close_command=RoborockCommand.CLOSE_DND_TIMER,
        ),
        CacheableAttribute.dust_collection_mode: RoborockAttribute(
            attribute="dust_collection_mode",
            get_command=RoborockCommand.GET_DUST_COLLECTION_MODE,
            set_command=RoborockCommand.SET_DUST_COLLECTION_MODE,
        ),
        CacheableAttribute.flow_led_status: RoborockAttribute(
            attribute="flow_led_status",
            get_command=RoborockCommand.GET_FLOW_LED_STATUS,
            set_command=RoborockCommand.SET_FLOW_LED_STATUS,
        ),
        CacheableAttribute.identify_furniture_status: RoborockAttribute(
            attribute="identify_furniture_status",
            get_command=RoborockCommand.GET_IDENTIFY_FURNITURE_STATUS,
            set_command=RoborockCommand.SET_IDENTIFY_FURNITURE_STATUS,
        ),
        CacheableAttribute.identify_ground_material_status: RoborockAttribute(
            attribute="identify_ground_material_status",
            get_command=RoborockCommand.GET_IDENTIFY_GROUND_MATERIAL_STATUS,
            set_command=RoborockCommand.SET_IDENTIFY_GROUND_MATERIAL_STATUS,
        ),
        CacheableAttribute.led_status: RoborockAttribute(
            attribute="led_status",
            get_command=RoborockCommand.GET_LED_STATUS,
            set_command=RoborockCommand.SET_LED_STATUS,
        ),
        CacheableAttribute.server_timer: RoborockAttribute(
            attribute="server_timer",
            get_command=RoborockCommand.GET_SERVER_TIMER,
            add_command=RoborockCommand.SET_SERVER_TIMER,
            set_command=RoborockCommand.UPD_SERVER_TIMER,
            close_command=RoborockCommand.DEL_SERVER_TIMER,
        ),
        CacheableAttribute.smart_wash_params: RoborockAttribute(
            attribute="smart_wash_params",
            get_command=RoborockCommand.GET_SMART_WASH_PARAMS,
            set_command=RoborockCommand.SET_SMART_WASH_PARAMS,
        ),
        CacheableAttribute.timezone: RoborockAttribute(
            attribute="timezone", get_command=RoborockCommand.GET_TIMEZONE, set_command=RoborockCommand.SET_TIMEZONE
        ),
        CacheableAttribute.valley_electricity_timer: RoborockAttribute(
            attribute="valley_electricity_timer",
            get_command=RoborockCommand.GET_VALLEY_ELECTRICITY_TIMER,
            set_command=RoborockCommand.SET_VALLEY_ELECTRICITY_TIMER,
            close_command=RoborockCommand.CLOSE_VALLEY_ELECTRICITY_TIMER,
        ),
        CacheableAttribute.wash_towel_mode: RoborockAttribute(
            attribute="wash_towel_mode",
            get_command=RoborockCommand.GET_WASH_TOWEL_MODE,
            set_command=RoborockCommand.SET_WASH_TOWEL_MODE,
        ),
    }
    return cache_map


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
        cacheable_attribute = next((attr for attr in CacheableAttribute if attr == attribute), None)
        if cacheable_attribute:
            return ParserCommand(type=command_type, attribute=CacheableAttribute(cacheable_attribute))
    return None
