from __future__ import annotations

from enum import Enum
from typing import Any, Type, TypeVar

_StrEnumT = TypeVar("_StrEnumT", bound="RoborockEnum")


class RoborockEnum(str, Enum):
    def __new__(cls: Type[_StrEnumT], value: str, *args: Any, **kwargs: Any) -> _StrEnumT:
        """Create a new StrEnum instance."""
        if not isinstance(value, str):
            raise TypeError(f"{value!r} is not a string")
        return super().__new__(cls, value, *args, **kwargs)

    def __str__(self):
        return str(self.value)

    @classmethod
    def _missing_(cls: Type[_StrEnumT], code: object):
        return cls._member_map_.get(str(code))

    @classmethod
    def as_dict(cls: Type[_StrEnumT]):
        return {int(i.name): i.value for i in cls}

    @classmethod
    def values(cls: Type[_StrEnumT]):
        return list(cls.as_dict().values())

    @classmethod
    def keys(cls: Type[_StrEnumT]):
        return list(cls.as_dict().keys())

    @classmethod
    def items(cls: Type[_StrEnumT]):
        return cls.as_dict().items()

    @classmethod
    def __getitem__(cls: Type[_StrEnumT], item):
        return cls.__getitem__(item)


def create_code_enum(name: str, data: dict) -> RoborockEnum:
    return RoborockEnum(name, {str(key): value for key, value in data.items()})


RoborockStateCode = create_code_enum(
    "RoborockStateCode",
    {
        1: "starting",
        2: "charger_disconnected",
        3: "idle",
        4: "remote_control_active",
        5: "cleaning",
        6: "returning_home",
        7: "manual_mode",
        8: "charging",
        9: "charging_problem",
        10: "paused",
        11: "spot_cleaning",
        12: "error",
        13: "shutting_down",
        14: "updating",
        15: "docking",
        16: "going_to_target",
        17: "zoned_cleaning",
        18: "segment_cleaning",
        22: "emptying_the_bin",  # on s7+, see #1189
        23: "washing_the_mop",  # on a46, #1435
        26: "going_to_wash_the_mop",  # on a46, #1435
        100: "charging_complete",
        101: "device_offline",
    },
)

RoborockErrorCode = create_code_enum(
    "RoborockErrorCode",
    {
        0: "none",
        1: "lidar_blocked",
        2: "bumper_stuck",
        3: "wheels_suspended",
        4: "cliff_sensor_error",
        5: "main_brush_jammed",
        6: "side_brush_jammed",
        7: "wheels_jammed",
        8: "robot_trapped",
        9: "no_dustbin",
        12: "low_battery",
        13: "charging_error",
        14: "battery_error",
        15: "wall_sensor_dirty",
        16: "robot_tilted",
        17: "side_brush_error",
        18: "fan_error",
        21: "vertical_bumper_pressed",
        22: "dock_locator_error",
        23: "return_to_dock_fail",
        24: "nogo_zone_detected",
        27: "vibrarise_jammed",
        28: "robot_on_carpet",
        29: "filter_blocked",
        30: "invisible_wall_detected",
        31: "cannot_cross_carpet",
        32: "internal_error",
    },
)

RoborockFanPowerCode = create_code_enum(
    "RoborockFanPowerCode",
    {
        105: "off",
        101: "silent",
        102: "balanced",
        103: "turbo",
        104: "max",
        108: "max_plus",
        106: "custom",
    },
)

RoborockMopModeCode = create_code_enum(
    "RoborockMopModeCode",
    {
        300: "standard",
        301: "deep",
        303: "deep_plus",
        302: "custom",
    },
)

RoborockMopIntensityCode = create_code_enum(
    "RoborockMopIntensityCode",
    {
        200: "off",
        201: "mild",
        202: "moderate",
        203: "intense",
        204: "custom",
    },
)

RoborockDockErrorCode = create_code_enum(
    "RoborockDockErrorCode",
    {
        0: "ok",
        38: "water empty",
        39: "waste water tank full",
    },
)

RoborockDockTypeCode = create_code_enum(
    "RoborockDockTypeCode",
    {0: "no_dock", 1: "unknown", 2: "unknown", 3: "empty_wash_fill_dock", 4: "unknown", 5: "auto_empty_dock_pure"},
)

RoborockDockDustCollectionModeCode = create_code_enum(
    "RoborockDockDustCollectionModeCode",
    {
        0: "smart",
        1: "light",
        2: "balanced",
        4: "max",
    },
)

RoborockDockWashTowelModeCode = create_code_enum(
    "RoborockDockWashTowelModeCode",
    {
        0: "light",
        1: "balanced",
        2: "deep",
    },
)
