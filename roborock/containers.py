from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Optional, Type

from dacite import Config, from_dict

from .code_mappings import (
    ModelSpecification,
    RoborockDockDustCollectionModeCode,
    RoborockDockErrorCode,
    RoborockDockTypeCode,
    RoborockDockWashTowelModeCode,
    RoborockErrorCode,
    RoborockFanPowerCode,
    RoborockMopIntensityCode,
    RoborockMopModeCode,
    RoborockStateCode,
    model_specifications,
)
from .const import (
    FILTER_REPLACE_TIME,
    MAIN_BRUSH_REPLACE_TIME,
    ROBOROCK_S7_MAXV,
    SENSOR_DIRTY_REPLACE_TIME,
    SIDE_BRUSH_REPLACE_TIME,
)

_LOGGER = logging.getLogger(__name__)


def camelize(s: str):
    first, *others = s.split("_")
    if len(others) == 0:
        return s
    return "".join([first.lower(), *map(str.title, others)])


def decamelize(s: str):
    return re.sub("([A-Z]+)", "_\\1", s).lower()


def decamelize_obj(d: dict | list, ignore_keys: list[str]):
    if isinstance(d, RoborockBase):
        d = d.as_dict()
    if isinstance(d, list):
        return [decamelize_obj(i, ignore_keys) if isinstance(i, (dict, list)) else i for i in d]
    return {
        (decamelize(a) if a not in ignore_keys else a): decamelize_obj(b, ignore_keys)
        if isinstance(b, (dict, list))
        else b
        for a, b in d.items()
    }


@dataclass
class RoborockBase:
    _ignore_keys = []  # type: ignore

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        ignore_keys = cls._ignore_keys
        return from_dict(cls, decamelize_obj(data, ignore_keys), config=Config(cast=[Enum]))

    def as_dict(self) -> dict:
        return asdict(
            self,
            dict_factory=lambda _fields: {camelize(key): value for (key, value) in _fields if value is not None},
        )


@dataclass
class Reference(RoborockBase):
    r: Optional[str] = None
    a: Optional[str] = None
    m: Optional[str] = None
    l: Optional[str] = None


@dataclass
class RRiot(RoborockBase):
    u: str
    s: str
    h: str
    k: str
    r: Reference


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
    model_specification: Optional[ModelSpecification] = None

    def __post_init__(self):
        if self.model not in model_specifications:
            _LOGGER.warning("We don't have specific device information for your model, please open an issue.")
            self.model_specification = model_specifications.get(ROBOROCK_S7_MAXV)
        else:
            self.model_specification = model_specifications.get(self.model)


@dataclass
class HomeDataDeviceStatus(RoborockBase):
    id: Optional[Any] = None
    name: Optional[Any] = None
    code: Optional[Any] = None
    model: Optional[str] = None
    icon_url: Optional[Any] = None
    attribute: Optional[Any] = None
    capability: Optional[Any] = None
    category: Optional[Any] = None
    schema: Optional[Any] = None
    model_specification: Optional[ModelSpecification] = None


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

    def get_all_devices(self) -> list[HomeDataDevice]:
        devices = []
        if self.devices is not None:
            devices += self.devices
        if self.received_devices is not None:
            devices += self.received_devices
        return devices


@dataclass
class LoginData(RoborockBase):
    user_data: UserData
    email: str
    home_data: Optional[HomeData] = None


@dataclass
class Status(RoborockBase):
    msg_ver: Optional[int] = None
    msg_seq: Optional[int] = None
    state: Optional[RoborockStateCode] = None
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
    fan_power: Optional[int] = None
    fan_power_enum: Optional[Type[RoborockFanPowerCode]] = None
    dnd_enabled: Optional[int] = None
    map_status: Optional[int] = None
    is_locating: Optional[int] = None
    lock_status: Optional[int] = None
    water_box_mode: Optional[int] = None
    water_box_mode_enum: Optional[Type[RoborockMopIntensityCode]] = None
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
    mop_mode: Optional[int] = None
    mop_mode_enum: Optional[Type[RoborockMopModeCode]] = None
    debug_mode: Optional[int] = None
    collision_avoid_status: Optional[int] = None
    switch_map_mode: Optional[int] = None
    dock_error_status: Optional[RoborockDockErrorCode] = None
    charge_status: Optional[int] = None
    unsave_map_reason: Optional[int] = None
    unsave_map_flag: Optional[int] = None

    def update_status(self, model_specification: ModelSpecification) -> None:
        self.fan_power_enum = model_specification.fan_power_code.as_enum_dict()[self.fan_power]
        if model_specification.mop_mode_code is not None:
            self.mop_mode_enum = model_specification.mop_mode_code.as_enum_dict()[self.mop_mode]
        if model_specification.mop_intensity_code is not None:
            self.water_box_mode_enum = model_specification.mop_intensity_code.as_enum_dict()[self.water_box_mode]


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
    main_brush_time_left: Optional[int] = None
    side_brush_time_left: Optional[int] = None
    filter_time_left: Optional[int] = None
    sensor_time_left: Optional[int] = None

    def __post_init__(self):
        self.main_brush_time_left = (
            MAIN_BRUSH_REPLACE_TIME - self.main_brush_work_time if self.main_brush_work_time else None
        )
        self.side_brush_time_left = (
            SIDE_BRUSH_REPLACE_TIME - self.side_brush_work_time if self.side_brush_work_time else None
        )
        self.filter_time_left = FILTER_REPLACE_TIME - self.filter_work_time if self.filter_work_time else None
        self.sensor_time_left = SENSOR_DIRTY_REPLACE_TIME - self.sensor_dirty_time if self.sensor_dirty_time else None


@dataclass
class MultiMapsListMapInfoBakMaps(RoborockBase):
    mapflag: Optional[Any] = None
    add_time: Optional[Any] = None


@dataclass
class MultiMapsListMapInfo(RoborockBase):
    _ignore_keys = ["mapFlag"]

    mapFlag: Optional[Any] = None
    add_time: Optional[Any] = None
    length: Optional[Any] = None
    name: Optional[Any] = None
    bak_maps: Optional[list[MultiMapsListMapInfoBakMaps]] = None


@dataclass
class MultiMapsList(RoborockBase):
    _ignore_keys = ["mapFlag"]

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
    mode: Optional[RoborockDockDustCollectionModeCode] = None


@dataclass
class WashTowelMode(RoborockBase):
    wash_mode: Optional[RoborockDockWashTowelModeCode] = None


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
    model_specification: ModelSpecification


@dataclass
class RoomMapping(RoborockBase):
    segment_id: int
    iot_id: str
