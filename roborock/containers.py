from __future__ import annotations

import datetime
import logging
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, NamedTuple, Optional, Type

from dacite import Config, from_dict

from .code_mappings import (
    RoborockDockDustCollectionModeCode,
    RoborockDockErrorCode,
    RoborockDockTypeCode,
    RoborockDockWashTowelModeCode,
    RoborockErrorCode,
    RoborockFanPowerCode,
    RoborockFanSpeedP10,
    RoborockFanSpeedQ7Max,
    RoborockFanSpeedS6Pure,
    RoborockFanSpeedS7,
    RoborockFanSpeedS7MaxV,
    RoborockMopIntensityCode,
    RoborockMopIntensityS7,
    RoborockMopIntensityV2,
    RoborockMopModeCode,
    RoborockMopModeS7,
    RoborockMopModeS8ProUltra,
    RoborockStateCode,
)
from .const import (
    FILTER_REPLACE_TIME,
    MAIN_BRUSH_REPLACE_TIME,
    ROBOROCK_G10S_PRO,
    ROBOROCK_P10,
    ROBOROCK_Q7_MAX,
    ROBOROCK_S4_MAX,
    ROBOROCK_S5_MAX,
    ROBOROCK_S6,
    ROBOROCK_S6_MAXV,
    ROBOROCK_S6_PURE,
    ROBOROCK_S7,
    ROBOROCK_S7_MAXV,
    ROBOROCK_S8,
    ROBOROCK_S8_PRO_ULTRA,
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
    is_cached = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        if isinstance(data, dict):
            ignore_keys = cls._ignore_keys
            return from_dict(cls, decamelize_obj(data, ignore_keys), config=Config(cast=[Enum]))

    def as_dict(self) -> dict:
        return asdict(
            self,
            dict_factory=lambda _fields: {
                camelize(key): value.value if isinstance(value, Enum) else value
                for (key, value) in _fields
                if value is not None
            },
        )


@dataclass
class RoborockBaseTimer(RoborockBase):
    start_hour: Optional[int] = None
    start_minute: Optional[int] = None
    end_hour: Optional[int] = None
    end_minute: Optional[int] = None
    enabled: Optional[int] = None
    start_time: Optional[datetime.time] = None
    end_time: Optional[datetime.time] = None

    def __post_init__(self) -> None:
        self.start_time = (
            datetime.time(hour=self.start_hour, minute=self.start_minute)
            if self.start_hour is not None and self.start_minute is not None
            else None
        )
        self.end_time = (
            datetime.time(hour=self.end_hour, minute=self.end_minute)
            if self.end_hour is not None and self.end_minute is not None
            else None
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
    device_status: Optional[dict] = None
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
    square_meter_clean_area: Optional[float] = None
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
    water_box_mode: Optional[RoborockMopIntensityCode] = None
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
    wash_status: Optional[int] = None
    distance_off: Optional[int] = None
    in_warmup: Optional[int] = None
    dry_status: Optional[int] = None
    rdt: Optional[int] = None
    clean_percent: Optional[int] = None
    rss: Optional[int] = None
    dss: Optional[int] = None
    common_status: Optional[int] = None
    corner_clean_mode: Optional[int] = None

    def __post_init__(self) -> None:
        self.square_meter_clean_area = round(self.clean_area / 1000000, 1) if self.clean_area is not None else None


@dataclass
class S4MaxStatus(Status):
    fan_power: Optional[RoborockFanSpeedS6Pure] = None
    water_box_mode: Optional[RoborockMopIntensityS7] = None
    mop_mode: Optional[RoborockMopModeS7] = None


@dataclass
class S5MaxStatus(Status):
    fan_power: Optional[RoborockFanSpeedS6Pure] = None
    water_box_mode: Optional[RoborockMopIntensityV2] = None


@dataclass
class Q7MaxStatus(Status):
    fan_power: Optional[RoborockFanSpeedQ7Max] = None
    water_box_mode: Optional[RoborockMopIntensityV2] = None


@dataclass
class S6MaxVStatus(Status):
    fan_power: Optional[RoborockFanSpeedS7MaxV] = None
    water_box_mode: Optional[RoborockMopIntensityS7] = None


@dataclass
class S6PureStatus(Status):
    fan_power: Optional[RoborockFanSpeedS6Pure] = None


@dataclass
class S7MaxVStatus(Status):
    fan_power: Optional[RoborockFanSpeedS7MaxV] = None
    water_box_mode: Optional[RoborockMopIntensityS7] = None
    mop_mode: Optional[RoborockMopModeS7] = None


@dataclass
class S7Status(Status):
    fan_power: Optional[RoborockFanSpeedS7] = None
    water_box_mode: Optional[RoborockMopIntensityS7] = None
    mop_mode: Optional[RoborockMopModeS7] = None


@dataclass
class S8ProUltraStatus(Status):
    fan_power: Optional[RoborockFanSpeedS7MaxV] = None
    water_box_mode: Optional[RoborockMopIntensityS7] = None
    mop_mode: Optional[RoborockMopModeS8ProUltra] = None


@dataclass
class S8Status(Status):
    fan_power: Optional[RoborockFanSpeedS7MaxV] = None
    water_box_mode: Optional[RoborockMopIntensityS7] = None
    mop_mode: Optional[RoborockMopModeS8ProUltra] = None


@dataclass
class P10Status(Status):
    fan_power: Optional[RoborockFanSpeedP10] = None
    water_box_mode: Optional[RoborockMopIntensityV2] = None
    mop_mode: Optional[RoborockMopModeS8ProUltra] = None


ModelStatus: dict[str, Type[Status]] = {
    ROBOROCK_S4_MAX: S4MaxStatus,
    ROBOROCK_S5_MAX: S5MaxStatus,
    ROBOROCK_Q7_MAX: Q7MaxStatus,
    ROBOROCK_S6: S6PureStatus,
    ROBOROCK_S6_MAXV: S6MaxVStatus,
    ROBOROCK_S6_PURE: S6PureStatus,
    ROBOROCK_S7_MAXV: S7MaxVStatus,
    ROBOROCK_S7: S7Status,
    ROBOROCK_S8: S8Status,
    ROBOROCK_S8_PRO_ULTRA: S8ProUltraStatus,
    ROBOROCK_G10S_PRO: S7MaxVStatus,
    ROBOROCK_P10: P10Status,
}


@dataclass
class DnDTimer(RoborockBaseTimer):
    """DnDTimer"""


@dataclass
class ValleyElectricityTimer(RoborockBaseTimer):
    """ValleyElectricityTimer"""


@dataclass
class CleanSummary(RoborockBase):
    clean_time: Optional[int] = None
    clean_area: Optional[int] = None
    square_meter_clean_area: Optional[float] = None
    clean_count: Optional[int] = None
    dust_collection_count: Optional[int] = None
    records: Optional[list[int]] = None
    last_clean_t: Optional[int] = None

    def __post_init__(self) -> None:
        self.square_meter_clean_area = round(self.clean_area / 1000000, 1) if self.clean_area is not None else None


@dataclass
class CleanRecord(RoborockBase):
    begin: Optional[int] = None
    end: Optional[int] = None
    duration: Optional[int] = None
    area: Optional[int] = None
    square_meter_area: Optional[float] = None
    error: Optional[int] = None
    complete: Optional[int] = None
    start_type: Optional[int] = None
    clean_type: Optional[int] = None
    finish_reason: Optional[int] = None
    dust_collection_status: Optional[int] = None
    avoid_count: Optional[int] = None
    wash_count: Optional[int] = None
    map_flag: Optional[int] = None

    def __post_init__(self) -> None:
        self.square_meter_area = round(self.area / 1000000, 1) if self.area is not None else None


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

    def __post_init__(self) -> None:
        self.main_brush_time_left = (
            MAIN_BRUSH_REPLACE_TIME - self.main_brush_work_time if self.main_brush_work_time is not None else None
        )
        self.side_brush_time_left = (
            SIDE_BRUSH_REPLACE_TIME - self.side_brush_work_time if self.side_brush_work_time is not None else None
        )
        self.filter_time_left = (
            FILTER_REPLACE_TIME - self.filter_work_time if self.filter_work_time is not None else None
        )
        self.sensor_time_left = (
            SENSOR_DIRTY_REPLACE_TIME - self.sensor_dirty_time if self.sensor_dirty_time is not None else None
        )


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
class DeviceData(RoborockBase):
    device: HomeDataDevice
    model: str
    host: Optional[str] = None


@dataclass
class RoomMapping(RoborockBase):
    segment_id: int
    iot_id: str


@dataclass
class ChildLockStatus(RoborockBase):
    lock_status: int


@dataclass
class FlowLedStatus(RoborockBase):
    status: int


@dataclass
class BroadcastMessage(RoborockBase):
    duid: str
    ip: str


class ServerTimer(NamedTuple):
    id: str
    status: str
    dontknow: int
