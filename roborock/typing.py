from __future__ import annotations

from enum import Enum

from .containers import Status, CleanSummary, Consumable, \
    DNDTimer, CleanRecord, SmartWashParameters, DustCollectionMode, WashTowelMode


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
    GET_MAP_V1 = "get_map_v1",
    GET_STATUS = "get_status"
    GET_DND_TIMER = "get_dnd_timer"
    GET_CLEAN_SUMMARY = "get_clean_summary"
    GET_CLEAN_RECORD = "get_clean_record"
    GET_CONSUMABLE = "get_consumable"
    GET_MULTI_MAPS_LIST = "get_multi_maps_list",
    APP_START = "app_start",
    APP_PAUSE = "app_pause",
    APP_STOP = "app_stop",
    APP_CHARGE = "app_charge",
    APP_SPOT = "app_spot",
    FIND_ME = "find_me",
    RESUME_ZONED_CLEAN = "resume_zoned_clean",
    RESUME_SEGMENT_CLEAN = "resume_segment_clean",
    SET_CUSTOM_MODE = "set_custom_mode",
    SET_MOP_MODE = "set_mop_mode",
    SET_WATER_BOX_CUSTOM_MODE = "set_water_box_custom_mode",
    RESET_CONSUMABLE = "reset_consumable",
    LOAD_MULTI_MAP = "load_multi_map",
    APP_RC_START = "app_rc_start",
    APP_RC_END = "app_rc_end",
    APP_RC_MOVE = "app_rc_move",
    APP_GOTO_TARGET = "app_goto_target",
    APP_SEGMENT_CLEAN = "app_segment_clean",
    APP_ZONED_CLEAN = "app_zoned_clean",
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
    APP_GET_INIT_STATUS = "get_init_status"
    SET_APP_TIMEZONE = "set_app_timezone"
    GET_NETWORK_INFO = "get_network_info"


class RoborockDockSummary:
    def __init__(self, dust_collection_mode: DustCollectionMode,
                 washing_mode_type: WashTowelMode, mop_wash: SmartWashParameters) -> None:
        self.dust_collection_mode = dust_collection_mode.mode.value
        self.washing_mode_type = washing_mode_type.wash_mode.value
        self.mop_wash_interval = mop_wash.wash_interval
        self.mop_wash_mode = mop_wash.smart_wash


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
