from dataclasses import dataclass
from typing import Any, Optional

from dacite import from_dict

from .code_mappings import RoborockDockType, RoborockDockDustCollectionType, \
    RoborockDockWashingModeType

OptionalAny: Optional[Any] = None
OptionalStr: Optional[str] = None
OptionalInt: Optional[int] = None
OptionalBool: Optional[bool] = None


@dataclass
class RoborockBase(dict):
    def __init__(self, data: dict[str, any]) -> None:
        super().__init__()
        if isinstance(data, dict):
            self.update(data)

    @classmethod
    def from_dict(cls, data: dict[str, any]):
        return from_dict(cls, data)

    def as_dict(self):
        return self.__dict__


@dataclass
class Reference(RoborockBase):
    region = OptionalStr
    api = OptionalStr
    mqtt = OptionalStr
    l_unknown = OptionalStr


@dataclass
class RRiot(RoborockBase):
    user = OptionalStr
    password = OptionalStr
    h_unknown = OptionalStr
    endpoint = OptionalStr
    reference: Reference


@dataclass
class UserData(RoborockBase):
    uid = OptionalInt
    token_type = OptionalStr
    token = OptionalStr
    rr_uid = OptionalStr
    region = OptionalStr
    country_code = OptionalStr
    country = OptionalStr
    nickname = OptionalStr
    rriot: RRiot
    tuya_device_state = OptionalInt
    avatar_url = OptionalStr


@dataclass
class HomeDataProductSchema(RoborockBase):
    id = OptionalAny
    name = OptionalAny
    code = OptionalAny
    mode = OptionalAny
    type = OptionalAny
    product_property = OptionalAny
    desc = OptionalAny


@dataclass
class HomeDataProduct(RoborockBase):
    id = OptionalStr
    name = OptionalStr
    code = OptionalStr
    model = OptionalStr
    iconurl = OptionalStr
    attribute = OptionalAny
    capability = OptionalInt
    category = OptionalStr
    schema: list[HomeDataProductSchema]


@dataclass
class HomeDataDeviceStatus(RoborockBase):
    id = OptionalAny
    name = OptionalAny
    code = OptionalAny
    model = OptionalAny
    icon_url = OptionalAny
    attribute = OptionalAny
    capability = OptionalAny
    category = OptionalAny
    schema = OptionalAny


@dataclass
class HomeDataDevice(RoborockBase):
    duid: str
    name: str
    local_key: str
    fv: str
    attribute = OptionalAny
    activetime = OptionalInt
    runtime_env = OptionalAny
    time_zone_id = OptionalStr
    icon_url = OptionalStr
    product_id = OptionalStr
    lon = OptionalAny
    lat = OptionalAny
    share = OptionalAny
    share_time = OptionalAny
    online = OptionalBool
    pv = OptionalStr
    room_id = OptionalAny
    tuya_uuid = OptionalAny
    tuya_migrated = OptionalBool
    extra = OptionalAny
    sn = OptionalStr
    feature_set = OptionalStr
    new_feature_set = OptionalStr
    device_status: Optional[HomeDataDeviceStatus] = None
    silent_ota_switch = OptionalBool


@dataclass
class HomeDataRoom(RoborockBase):
    id = OptionalAny
    name = OptionalAny


@dataclass
class HomeData(RoborockBase):
    id = OptionalInt
    name = OptionalStr
    lon = OptionalAny
    lat = OptionalAny
    geo_name = OptionalAny
    products: list[HomeDataProduct]
    devices: list[HomeDataDevice]
    received_devices: list[HomeDataDevice]
    rooms: list[HomeDataRoom]


@dataclass
class LoginData(RoborockBase):
    user_data: UserData
    home_data: HomeData
    email = OptionalStr


@dataclass
class Status(RoborockBase):
    msg_ver = OptionalInt
    msg_seq = OptionalInt
    status = OptionalStr
    state = OptionalInt
    battery = OptionalInt
    clean_time = OptionalInt
    clean_area = OptionalInt
    error_code = OptionalInt
    error = OptionalStr
    map_present = OptionalInt
    in_cleaning = OptionalInt
    in_returning = OptionalInt
    in_fresh_state = OptionalInt
    lab_status = OptionalInt
    water_box_status = OptionalInt
    back_type = OptionalInt
    wash_phase = OptionalInt
    wash_ready = OptionalInt
    fan_power_code = OptionalInt
    fan_power = OptionalStr
    dnd_enabled = OptionalInt
    map_status = OptionalInt
    is_locating = OptionalInt
    lock_status = OptionalInt
    water_box_mode = OptionalInt
    mop_intensity = OptionalStr
    water_box_carriage_status = OptionalInt
    mop_forbidden_enable = OptionalInt
    camera_status = OptionalInt
    is_exploring = OptionalInt
    home_sec_status = OptionalInt
    home_sec_enable_password = OptionalInt
    adbumper_status: list[int]
    water_shortage_status = OptionalInt
    dock_type_code = OptionalInt
    dock_type: RoborockDockType
    dust_collection_status = OptionalInt
    auto_dust_collection = OptionalInt
    avoid_count = OptionalInt
    mop_mode_code = OptionalInt
    mop_mode = OptionalStr
    debug_mode = OptionalInt
    collision_avoid_status = OptionalInt
    switch_map_mode = OptionalInt
    dock_error_status_code = OptionalInt
    dock_error_status = OptionalStr
    charge_status = OptionalInt
    unsave_map_reason = OptionalInt
    unsave_map_flag = OptionalInt


@dataclass
class DNDTimer(RoborockBase):
    start_hour = OptionalInt
    start_minute = OptionalInt
    end_hour = OptionalInt
    end_minute = OptionalInt
    enabled = OptionalInt


@dataclass
class CleanSummary(RoborockBase):
    clean_time = OptionalInt
    clean_area = OptionalInt
    clean_count = OptionalInt
    dust_collection_count = OptionalInt
    records: list[int]


@dataclass
class CleanRecord(RoborockBase):
    begin = OptionalInt
    end = OptionalInt
    duration = OptionalInt
    area = OptionalInt
    error = OptionalInt
    complete = OptionalInt
    start_type = OptionalInt
    clean_type = OptionalInt
    finish_reason = OptionalInt
    dust_collection_status = OptionalInt
    avoid_count = OptionalInt
    wash_count = OptionalInt
    map_flag = OptionalInt


@dataclass
class Consumable(RoborockBase):
    main_brush_work_time = OptionalInt
    side_brush_work_time = OptionalInt
    filter_work_time = OptionalInt
    filter_element_work_time = OptionalInt
    sensor_dirty_time = OptionalInt
    strainer_work_times = OptionalInt
    dust_collection_work_times = OptionalInt
    cleaning_brush_work_times = OptionalInt


@dataclass
class MultiMapsListMapInfoBakMaps(RoborockBase):
    mapflag = OptionalAny
    add_time = OptionalAny


@dataclass
class MultiMapsListMapInfo(RoborockBase):
    mapflag = OptionalAny
    add_time = OptionalAny
    length = OptionalAny
    name = OptionalAny
    bak_maps: list[MultiMapsListMapInfoBakMaps]


@dataclass
class MultiMapsList(RoborockBase):
    max_multi_map = OptionalInt
    max_bak_map = OptionalInt
    multi_map_count = OptionalInt
    map_info: list[MultiMapsListMapInfo]


@dataclass
class SmartWashParams(RoborockBase):
    smart_wash = OptionalInt
    wash_interval = OptionalInt


@dataclass
class DustCollectionMode(RoborockBase):
    mode: RoborockDockDustCollectionType


@dataclass
class WashTowelMode(RoborockBase):
    wash_mode: RoborockDockWashingModeType


@dataclass
class NetworkInfo(RoborockBase):
    ip: str
    ssid = OptionalStr
    mac = OptionalStr
    bssid = OptionalStr
    rssi = OptionalInt


@dataclass
class RoborockDeviceInfo(RoborockBase):
    device: HomeDataDevice


@dataclass
class RoborockLocalDeviceInfo(RoborockDeviceInfo):
    network_info: NetworkInfo
