from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .containers import Status, CleanSummary, Consumable, \
    DNDTimer, CleanRecord, SmartWashParams, DustCollectionMode, WashTowelMode


class RoborockDevicePropField(str, Enum):
    STATUS = "status"
    DND_TIMER = "dnd_timer"
    CLEAN_SUMMARY = "clean_summary"
    CONSUMABLE = "consumable"
    LAST_CLEAN_RECORD = "last_clean_record"
    DOCK_SUMMARY = "dock_summary"


class RoborockDockSummaryField(str, Enum):
    DUST_COLLECTION_MODE = "dust_collection_mode"
    WASHING_MODE_TYPE = "washing_mode_type"
    MOP_WASH = "mop_wash"


class RoborockCommand(str, Enum):
    GET_PROP = "get_prop"
    GET_MAP_V1 = "get_map_v1"
    GET_STATUS = "get_status"
    GET_DND_TIMER = "get_dnd_timer"
    GET_CLEAN_SUMMARY = "get_clean_summary"
    GET_CLEAN_RECORD = "get_clean_record"
    GET_CONSUMABLE = "get_consumable"
    GET_MULTI_MAPS_LIST = "get_multi_maps_list"
    APP_START = "app_start"
    APP_PAUSE = "app_pause"
    APP_STOP = "app_stop"
    APP_CHARGE = "app_charge"
    APP_SPOT = "app_spot"
    FIND_ME = "find_me"
    RESUME_ZONED_CLEAN = "resume_zoned_clean"
    RESUME_SEGMENT_CLEAN = "resume_segment_clean"
    SET_CUSTOM_MODE = "set_custom_mode"
    SET_MOP_MODE = "set_mop_mode"
    SET_WATER_BOX_CUSTOM_MODE = "set_water_box_custom_mode"
    RESET_CONSUMABLE = "reset_consumable"
    LOAD_MULTI_MAP = "load_multi_map"
    APP_RC_START = "app_rc_start"
    APP_RC_END = "app_rc_end"
    APP_RC_MOVE = "app_rc_move"
    APP_GOTO_TARGET = "app_goto_target"
    APP_SEGMENT_CLEAN = "app_segment_clean"
    APP_ZONED_CLEAN = "app_zoned_clean"
    APP_GET_DRYER_SETTING = "app_get_dryer_setting"
    APP_SET_DRYER_SETTING = "app_set_dryer_setting"
    APP_START_WASH = "app_start_wash"
    APP_STOP_WASH = "app_stop_wash"
    GET_DUST_COLLECTION_MODE = "get_dust_collection_mode"
    SET_DUST_COLLECTION_MODE = "set_dust_collection_mode"
    GET_SMART_WASH_PARAMS = "get_smart_wash_params"
    SET_SMART_WASH_PARAMS = "set_smart_wash_params"
    GET_WASH_TOWEL_MODE = "get_wash_towel_mode"
    SET_WASH_TOWEL_MODE = "set_wash_towel_mode"
    SET_CHILD_LOCK_STATUS = "set_child_lock_status"
    GET_CHILD_LOCK_STATUS = "get_child_lock_status"
    START_WASH_THEN_CHARGE = "start_wash_then_charge"
    GET_CURRENT_SOUND = "get_current_sound"
    GET_SERIAL_NUMBER = "get_serial_number"
    GET_TIMEZONE = "get_timezone"
    GET_SERVER_TIMER = "get_server_timer"
    GET_CUSTOMIZE_CLEAN_MODE = "get_customize_clean_mode"
    GET_CLEAN_SEQUENCE = "get_clean_sequence"
    SET_FDS_ENDPOINT = "set_fds_endpoint"  # Seems to be logging server
    ENABLE_LOG_UPLOAD = "enable_log_upload"
    APP_WAKEUP_ROBOT = "app_wakeup_robot"
    GET_LED_STATUS = "get_led_status"
    GET_FLOW_LED_STATUS = "get_flow_led_status"
    SET_FLOW_LED_STATUS = "set_flow_led_status"
    GET_SOUND_PROGRESS = "get_sound_progress"
    GET_SOUND_VOLUME = "get_sound_volume"
    TEST_SOUND_VOLUME = "test_sound_volume"
    CHANGE_SOUND_VOLUME = "change_sound_volume"
    GET_CARPET_MODE = "get_carpet_mode"
    SET_CARPET_MODE = "set_carpet_mode"
    GET_CARPET_CLEAN_MODE = "get_carpet_clean_mode"
    SET_CARPET_CLEAN_MODE = "set_carpet_clean_mode"
    UPD_SERVER_TIMER = "upd_server_timer"  # Server timer seems to be with schedules
    SET_SERVER_TIMER = "set_server_timer"
    SET_APP_TIMEZONE = "set_app_timezone"
    GET_NETWORK_INFO = "get_network_info"
    GET_IDENTIFY_FURNITURE_STATUS = "get_identify_furniture_status"
    SET_CAMERA_STATUS = "set_camera_status"
    SET_DND_TIMER = "set_dnd_timer"
    GET_COLLISION_AVOID_STATUS = "get_collision_avoid_status"
    CLOSE_VALLEY_ELECTRICITY_TIMER = "close_valley_electricity_timer"
    GET_VALLEY_ELECTRICITY_TIMER = "get_valley_electricity_timer"
    SET_CLEAN_MOTOR_MODE = "set_clean_motor_mode"
    SET_LED_STATUS = "set_led_status"
    GET_CAMERA_STATUS = "get_camera_status"
    CLOSE_DND_TIMER = "close_dnd_timer"
    GET_MULTI_MAP = "get_multi_map"
    SET_COLLISION_AVOID_STATUS = "set_collision_avoid_status"
    SET_IDENTIFY_GROUND_MATERIAL_STATUS = "set_identify_ground_material_status"
    GET_IDENTIFY_GROUND_MATERIAL_STATUS = "get_identify_ground_material_status"
    SET_VALLEY_ELECTRICITY_TIMER = "set_valley_electricity_timer"
    SWITCH_WATER_MARK = "switch_water_mark"
    SET_IDENTIFY_FURNITURE_STATUS = "set_identify_furniture_status"
    GET_CLEAN_RECORD_MAP = "get_clean_record_map"


@dataclass
class CommandInfo:
    prefix: bytes


CommandInfoMap: dict[RoborockCommand, CommandInfo] = {
    RoborockCommand.GET_PROP: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_STATUS: CommandInfo(prefix=b'\x00\x00\x00\x77'),
    RoborockCommand.SET_CUSTOM_MODE: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_CHILD_LOCK_STATUS: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_MULTI_MAPS_LIST: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_IDENTIFY_FURNITURE_STATUS: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.SET_WATER_BOX_CUSTOM_MODE: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_CLEAN_SEQUENCE: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_CUSTOMIZE_CLEAN_MODE: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_CARPET_CLEAN_MODE: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.SET_CAMERA_STATUS: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.SET_DND_TIMER: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_FLOW_LED_STATUS: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_COLLISION_AVOID_STATUS: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.CLOSE_VALLEY_ELECTRICITY_TIMER: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.SET_FLOW_LED_STATUS: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_VALLEY_ELECTRICITY_TIMER: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_CLEAN_RECORD: CommandInfo(prefix=b'\x00\x00\x00\x87'),
    RoborockCommand.GET_MAP_V1: CommandInfo(prefix=b'\x00\x00\x00\xc7'),
    RoborockCommand.SET_CLEAN_MOTOR_MODE: CommandInfo(prefix=b'\x00\x00\x00\xb7'),
    RoborockCommand.GET_CONSUMABLE: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_SERVER_TIMER: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_SERIAL_NUMBER: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_CURRENT_SOUND: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.SET_LED_STATUS: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_CAMERA_STATUS: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_PAUSE: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_CLEAN_SUMMARY: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_NETWORK_INFO: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_LED_STATUS: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.CLOSE_DND_TIMER: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_WAKEUP_ROBOT: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.SET_MOP_MODE: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_DND_TIMER: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_CARPET_MODE: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.GET_TIMEZONE: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.SET_CARPET_MODE: CommandInfo(prefix=b'\x00\x00\x00\xd7'),
    RoborockCommand.GET_MULTI_MAP: CommandInfo(prefix=b'\x00\x00\x00\xd7'),
    RoborockCommand.SET_COLLISION_AVOID_STATUS: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.SET_CARPET_CLEAN_MODE: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.SET_IDENTIFY_GROUND_MATERIAL_STATUS: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.GET_IDENTIFY_GROUND_MATERIAL_STATUS: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.SET_VALLEY_ELECTRICITY_TIMER: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.SWITCH_WATER_MARK: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.SET_IDENTIFY_FURNITURE_STATUS: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.SET_CHILD_LOCK_STATUS: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.GET_CLEAN_RECORD_MAP: CommandInfo(prefix=b'\x00\x00\xe7'),
    RoborockCommand.APP_START: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_STOP: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_CHARGE: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_SPOT: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.FIND_ME: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.RESUME_ZONED_CLEAN: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.RESUME_SEGMENT_CLEAN: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.RESET_CONSUMABLE: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.LOAD_MULTI_MAP: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_RC_START: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_RC_END: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_RC_MOVE: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_GOTO_TARGET: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_SEGMENT_CLEAN: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_ZONED_CLEAN: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_START_WASH: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.APP_STOP_WASH: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.SET_FDS_ENDPOINT: CommandInfo(prefix=b'\x00\x00\x97'),
    RoborockCommand.ENABLE_LOG_UPLOAD: CommandInfo(prefix=b'\x00\x00\x87'),
    RoborockCommand.GET_SOUND_VOLUME: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.TEST_SOUND_VOLUME: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.UPD_SERVER_TIMER: CommandInfo(prefix=b'\x00\x00\x00w'),
    RoborockCommand.SET_APP_TIMEZONE: CommandInfo(prefix=b'\x00\x00\x97'),
    #TODO discover prefix for following commands
    # RoborockCommand.APP_GET_DRYER_SETTING: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.APP_SET_DRYER_SETTING: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.GET_DUST_COLLECTION_MODE: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.SET_DUST_COLLECTION_MODE: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.GET_SMART_WASH_PARAMS: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.SET_SMART_WASH_PARAMS: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.GET_WASH_TOWEL_MODE: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.SET_WASH_TOWEL_MODE: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.START_WASH_THEN_CHARGE: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.GET_SOUND_PROGRESS: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.CHANGE_SOUND_VOLUME: CommandInfo(prefix=b'\x00\x00\x00w'),
    # RoborockCommand.SET_SERVER_TIMER: CommandInfo(prefix=b'\x00\x00\x00w'),
}


class RoborockDockSummary:
    def __init__(self, dust_collection_mode: DustCollectionMode,
                 wash_towel_mode: WashTowelMode, smart_wash_params: SmartWashParams) -> None:
        self.dust_collection_mode = dust_collection_mode
        self.wash_towel_mode = wash_towel_mode
        self.smart_wash_params = smart_wash_params


class RoborockDeviceProp:
    def __init__(self, status: Status, dnd_timer: DNDTimer, clean_summary: CleanSummary, consumable: Consumable,
                 last_clean_record: CleanRecord = None, dock_summary: RoborockDockSummary = None):
        self.status = status
        self.dnd_timer = dnd_timer
        self.clean_summary = clean_summary
        self.consumable = consumable
        self.last_clean_record = last_clean_record
        self.dock_summary = dock_summary

    def update(self, device_prop: 'RoborockDeviceProp'):
        if device_prop.status:
            self.status = device_prop.status
        if device_prop.dnd_timer:
            self.dnd_timer = device_prop.dnd_timer
        if device_prop.clean_summary:
            self.clean_summary = device_prop.clean_summary
        if device_prop.consumable:
            self.consumable = device_prop.consumable
        if device_prop.last_clean_record:
            self.last_clean_record = device_prop.last_clean_record
        if device_prop.dock_summary:
            self.dock_summary = device_prop.dock_summary
