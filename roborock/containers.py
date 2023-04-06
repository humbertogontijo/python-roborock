import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from dacite import from_dict, Config

from roborock.code_mappings import RoborockDockWashTowelModeCode, RoborockDockTypeCode
from .code_mappings import RoborockMopModeCode, RoborockDockErrorCode, \
    RoborockErrorCode, RoborockDockDustCollectionModeCode, RoborockFanPowerCode


def to_snake(s):
    return re.sub('([A-Z]+)', '_\\1', s).lower()


def decamelize(d):
    if isinstance(d, list):
        return [decamelize(i) if isinstance(i, (dict, list)) else i for i in d]
    return {to_snake(a): decamelize(b) if isinstance(b, (dict, list)) else b for a, b in d.items()}


@dataclass
class RoborockBase(dict):
    def __init__(self, data: dict[str, any]) -> None:
        super().__init__()
        if isinstance(data, dict):
            self.update(data)

    @classmethod
    def from_dict(cls, data: dict[str, any]):
        return from_dict(cls, decamelize(data), config=Config(cast=[Enum]))

    def as_dict(self):
        return self.__dict__


@dataclass
class Reference(RoborockBase):
    r: Optional[str] = None
    a: Optional[str] = None
    m: Optional[str] = None
    l: Optional[str] = None


@dataclass
class RRiot(RoborockBase):
    u: Optional[str] = None
    s: Optional[str] = None
    h: Optional[str] = None
    k: Optional[str] = None
    r: Optional[Reference] = None


@dataclass
class UserData(RoborockBase):
    uid: Optional[int] = None
    tokentype: Optional[str] = None
    token: Optional[str] = None
    rruid: Optional[str] = None
    region: Optional[str] = None
    countrycode: Optional[str] = None
    country: Optional[str] = None
    nickname: Optional[str] = None
    rriot: Optional[RRiot] = None
    tuya_device_state: Optional[int] = None
    avatarurl: Optional[str] = None


@dataclass
class HomeDataProductSchema(RoborockBase):
    id: Optional[Any] = None
    name: Optional[Any] = None
    code: Optional[Any] = None
    mode: Optional[Any] = None
    type: Optional[Any] = None
    product_property: Optional[Any] = None
    desc: Optional[Any] = None


@dataclass
class HomeDataProduct(RoborockBase):
    id: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    model: Optional[str] = None
    iconurl: Optional[str] = None
    attribute: Optional[Any] = None
    capability: Optional[int] = None
    category: Optional[str] = None
    schema: Optional[list[HomeDataProductSchema]] = None


@dataclass
class HomeDataDeviceStatus(RoborockBase):
    id: Optional[Any] = None
    name: Optional[Any] = None
    code: Optional[Any] = None
    model: Optional[Any] = None
    icon_url: Optional[Any] = None
    attribute: Optional[Any] = None
    capability: Optional[Any] = None
    category: Optional[Any] = None
    schema: Optional[Any] = None


@dataclass
class HomeDataDevice(RoborockBase):
    duid: str
    name: str
    local_key: str
    fv: str
    attribute: Optional[Any] = None
    active_time: Optional[int] = None
    runtime_env: Optional[Any] = None
    time_zone_id: Optional[str] = None
    icon_url: Optional[str] = None
    product_id: Optional[str] = None
    lon: Optional[Any] = None
    lat: Optional[Any] = None
    share: Optional[Any] = None
    share_time: Optional[Any] = None
    online: Optional[bool] = None
    pv: Optional[str] = None
    room_id: Optional[Any] = None
    tuya_uuid: Optional[Any] = None
    tuya_migrated: Optional[bool] = None
    extra: Optional[Any] = None
    sn: Optional[str] = None
    feature_set: Optional[str] = None
    new_feature_set: Optional[str] = None
    device_status: Optional[HomeDataDeviceStatus] = None
    silent_ota_switch: Optional[bool] = None


@dataclass
class HomeDataRoom(RoborockBase):
    id: Optional[Any] = None
    name: Optional[Any] = None


@dataclass
class HomeData(RoborockBase):
    id: Optional[int] = None
    name: Optional[str] = None
    lon: Optional[Any] = None
    lat: Optional[Any] = None
    geo_name: Optional[Any] = None
    products: Optional[list[HomeDataProduct]] = None
    devices: Optional[list[HomeDataDevice]] = None
    received_devices: Optional[list[HomeDataDevice]] = None
    rooms: Optional[list[HomeDataRoom]] = None


@dataclass
class LoginData(RoborockBase):
    user_data: UserData
    home_data: HomeData
    email: Optional[str] = None


@dataclass
class Status(RoborockBase):
    msg_ver: Optional[int] = None
    msg_seq: Optional[int] = None
    status: Optional[str] = None
    state: Optional[int] = None
    battery: Optional[int] = None
    clean_time: Optional[int] = None
    clean_area: Optional[int] = None
    error_code: Optional[RoborockErrorCode] = None
    map_present: Optional[int] = None
    in_cleaning: Optional[int] = None
    in_returning: Optional[int] = None
    in_fresh_state: Optional[int] = None
    lab_status: Optional[int] = None
    water_box_status: Optional[int] = None
    back_type: Optional[int] = None
    wash_phase: Optional[int] = None
    wash_ready: Optional[int] = None
    fan_power: Optional[RoborockFanPowerCode] = None
    dnd_enabled: Optional[int] = None
    map_status: Optional[int] = None
    is_locating: Optional[int] = None
    lock_status: Optional[int] = None
    water_box_mode: Optional[int] = None
    mop_intensity: Optional[str] = None
    water_box_carriage_status: Optional[int] = None
    mop_forbidden_enable: Optional[int] = None
    camera_status: Optional[int] = None
    is_exploring: Optional[int] = None
    home_sec_status: Optional[int] = None
    home_sec_enable_password: Optional[int] = None
    adbumper_status: Optional[list[int]] = None
    water_shortage_status: Optional[int] = None
    dock_type: Optional[RoborockDockTypeCode] = None
    dust_collection_status: Optional[int] = None
    auto_dust_collection: Optional[int] = None
    avoid_count: Optional[int] = None
    mop_mode: Optional[RoborockMopModeCode] = None
    debug_mode: Optional[int] = None
    collision_avoid_status: Optional[int] = None
    switch_map_mode: Optional[int] = None
    dock_error_status: Optional[RoborockDockErrorCode] = None
    charge_status: Optional[int] = None
    unsave_map_reason: Optional[int] = None
    unsave_map_flag: Optional[int] = None


@dataclass
class DNDTimer(RoborockBase):
    start_hour: Optional[int] = None
    start_minute: Optional[int] = None
    end_hour: Optional[int] = None
    end_minute: Optional[int] = None
    enabled: Optional[int] = None


@dataclass
class CleanSummary(RoborockBase):
    clean_time: Optional[int] = None
    clean_area: Optional[int] = None
    clean_count: Optional[int] = None
    dust_collection_count: Optional[int] = None
    records: Optional[list[int]] = None


@dataclass
class CleanRecord(RoborockBase):
    begin: Optional[int] = None
    end: Optional[int] = None
    duration: Optional[int] = None
    area: Optional[int] = None
    error: Optional[int] = None
    complete: Optional[int] = None
    start_type: Optional[int] = None
    clean_type: Optional[int] = None
    finish_reason: Optional[int] = None
    dust_collection_status: Optional[int] = None
    avoid_count: Optional[int] = None
    wash_count: Optional[int] = None
    map_flag: Optional[int] = None


@dataclass
class Consumable(RoborockBase):
    main_brush_work_time: Optional[int] = None
    side_brush_work_time: Optional[int] = None
    filter_work_time: Optional[int] = None
    filter_element_work_time: Optional[int] = None
    sensor_dirty_time: Optional[int] = None
    strainer_work_times: Optional[int] = None
    dust_collection_work_times: Optional[int] = None
    cleaning_brush_work_times: Optional[int] = None


@dataclass
class MultiMapsListMapInfoBakMaps(RoborockBase):
    mapflag: Optional[Any] = None
    add_time: Optional[Any] = None


@dataclass
class MultiMapsListMapInfo(RoborockBase):
    mapflag: Optional[Any] = None
    add_time: Optional[Any] = None
    length: Optional[Any] = None
    name: Optional[Any] = None
    bak_maps: Optional[list[MultiMapsListMapInfoBakMaps]] = None


@dataclass
class MultiMapsList(RoborockBase):
    max_multi_map: Optional[int] = None
    max_bak_map: Optional[int] = None
    multi_map_count: Optional[int] = None
    map_info: Optional[list[MultiMapsListMapInfo]] = None


@dataclass
class SmartWashParams(RoborockBase):
    smart_wash: Optional[int] = None
    wash_interval: Optional[int] = None


@dataclass
class DustCollectionMode(RoborockBase):
    mode: RoborockDockDustCollectionModeCode


@dataclass
class WashTowelMode(RoborockBase):
    wash_mode: RoborockDockWashTowelModeCode


@dataclass
class NetworkInfo(RoborockBase):
    ip: str
    ssid: Optional[str] = None
    mac: Optional[str] = None
    bssid: Optional[str] = None
    rssi: Optional[int] = None


@dataclass
class RoborockDeviceInfo(RoborockBase):
    device: HomeDataDevice


@dataclass
class RoborockLocalDeviceInfo(RoborockDeviceInfo):
    network_info: NetworkInfo
