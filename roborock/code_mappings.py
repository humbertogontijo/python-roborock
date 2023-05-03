from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Type

from roborock.const import (
    ROBOROCK_Q7_MAX,
    ROBOROCK_S5_MAX,
    ROBOROCK_S6_MAXV,
    ROBOROCK_S6_PURE,
    ROBOROCK_S7,
    ROBOROCK_S7_MAXV,
    ROBOROCK_S8_PRO_ULTRA,
)

_LOGGER = logging.getLogger(__name__)


class RoborockEnum(IntEnum):
    """Roborock Enum for codes with int values"""

    @classmethod
    def _missing_(cls: Type[RoborockEnum], key) -> str:
        if hasattr(cls, "missing"):
            _LOGGER.warning(f"Missing {cls.__name__} code: {key} - defaulting to 'missing'")
            return cls.missing  # type: ignore
        _LOGGER.warning(f"Missing {cls.__name__} code: {key} - defaulting to {cls.keys()[0]}")
        return cls.keys()[0]

    @classmethod
    def as_dict(cls: Type[RoborockEnum]):
        return {i.value: i.name for i in cls if i.name != "missing"}

    @classmethod
    def as_enum_dict(cls: Type[RoborockEnum]):
        return {i.value: i for i in cls if i.name != "missing"}

    @classmethod
    def values(cls: Type[RoborockEnum]) -> list[int]:
        return list(cls.as_dict().values())

    @classmethod
    def keys(cls: Type[RoborockEnum]) -> list[str]:
        return list(cls.as_dict().keys())

    @classmethod
    def items(cls: Type[RoborockEnum]):
        return cls.as_dict().items()


class RoborockStateCode(RoborockEnum):
    starting = 1
    charger_disconnected = 2
    idle = 3
    remote_control_active = 4
    cleaning = 5
    returning_home = 6
    manual_mode = 7
    charging = 8
    charging_problem = 9
    paused = 10
    spot_cleaning = 11
    error = 12
    shutting_down = 13
    updating = 14
    docking = 15
    going_to_target = 16
    zoned_cleaning = 17
    segment_cleaning = 18
    emptying_the_bin = 22  # on s7+
    washing_the_mop = 23  # on a46
    going_to_wash_the_mop = 26  # on a46
    charging_complete = 100
    device_offline = 101


class RoborockErrorCode(RoborockEnum):
    none = 0
    lidar_blocked = 1
    bumper_stuck = 2
    wheels_suspended = 3
    cliff_sensor_error = 4
    main_brush_jammed = 5
    side_brush_jammed = 6
    wheels_jammed = 7
    robot_trapped = 8
    no_dustbin = 9
    low_battery = 12
    charging_error = 13
    battery_error = 14
    wall_sensor_dirty = 15
    robot_tilted = 16
    side_brush_error = 17
    fan_error = 18
    vertical_bumper_pressed = 21
    dock_locator_error = 22
    return_to_dock_fail = 23
    nogo_zone_detected = 24
    vibrarise_jammed = 27
    robot_on_carpet = 28
    filter_blocked = 29
    invisible_wall_detected = 30
    cannot_cross_carpet = 31
    internal_error = 32


class RoborockFanPowerCode(RoborockEnum):
    """Describes the fan power of the vacuum cleaner."""

    # Fan speeds should have the first letter capitalized - as there is no way to change the name in translations as
    # far as I am aware


class RoborockFanSpeedV1(RoborockFanPowerCode):
    silent = 38
    standard = 60
    medium = 77
    turbo = 90


class RoborockFanSpeedV2(RoborockFanPowerCode):
    silent = 101
    balanced = 102
    turbo = 103
    max = 104
    gentle = 105
    auto = 106


class RoborockFanSpeedV3(RoborockFanPowerCode):
    silent = 38
    standard = 60
    medium = 75
    turbo = 100


class RoborockFanSpeedE2(RoborockFanPowerCode):
    gentle = 41
    silent = 50
    standard = 68
    medium = 79
    turbo = 100


class RoborockFanSpeedS7(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106


class RoborockFanSpeedS7MaxV(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    max_plus = 108


class RoborockFanSpeedS6Pure(RoborockFanPowerCode):
    gentle = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104


class RoborockFanSpeedQ7Max(RoborockFanPowerCode):
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104


class RoborockMopModeCode(RoborockEnum):
    """Describes the mop mode of the vacuum cleaner."""


class RoborockMopModeS7(RoborockMopModeCode):
    """Describes the mop mode of the vacuum cleaner."""

    standard = 300
    deep = 301
    custom = 302
    deep_plus = 303


class RoborockMopModeS8ProUltra(RoborockMopModeCode):
    standard = 300
    deep = 301
    deep_plus = 303
    fast = 304


class RoborockMopIntensityCode(RoborockEnum):
    """Describes the mop intensity of the vacuum cleaner."""


class RoborockMopIntensityS7(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    mild = 201
    moderate = 202
    intense = 203
    custom = 204


class RoborockMopIntensityV2(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 207


class RoborockDockErrorCode(RoborockEnum):
    """Describes the error code of the dock."""

    ok = 0
    water_empty = 38
    waste_water_tank_full = 39


class RoborockDockTypeCode(RoborockEnum):
    missing = -9999
    no_dock = 0
    empty_wash_fill_dock = 3
    auto_empty_dock_pure = 5
    s8_dock = 7


class RoborockDockDustCollectionModeCode(RoborockEnum):
    """Describes the dust collection mode of the vacuum cleaner."""

    # TODO: Get the correct values for various different docks
    missing = -9999
    smart = 0
    light = 1
    balanced = 2
    max = 4


class RoborockDockWashTowelModeCode(RoborockEnum):
    """Describes the wash towel mode of the vacuum cleaner."""

    # TODO: Get the correct values for various different docks
    missing = -9999
    light = 0
    balanced = 1
    deep = 2


@dataclass
class ModelSpecification:
    model_name: str
    model_code: str
    fan_power_code: Type[RoborockFanPowerCode]
    mop_mode_code: Type[RoborockMopModeCode] | None
    mop_intensity_code: Type[RoborockMopIntensityCode] | None


model_specifications = {
    ROBOROCK_S5_MAX: ModelSpecification(
        model_name="Roborock S5 Max",
        model_code=ROBOROCK_S5_MAX,
        fan_power_code=RoborockFanSpeedS6Pure,
        mop_mode_code=None,
        mop_intensity_code=RoborockMopIntensityV2,
    ),
    ROBOROCK_Q7_MAX: ModelSpecification(
        model_name="Roborock Q7 Max",
        model_code=ROBOROCK_Q7_MAX,
        fan_power_code=RoborockFanSpeedQ7Max,
        mop_mode_code=None,
        mop_intensity_code=RoborockMopIntensityV2,
    ),
    ROBOROCK_S6_MAXV: ModelSpecification(
        model_name="Roborock S6 MaxV",
        model_code=ROBOROCK_S6_MAXV,
        fan_power_code=RoborockFanSpeedE2,
        mop_mode_code=None,
        mop_intensity_code=RoborockMopIntensityV2,
    ),
    ROBOROCK_S6_PURE: ModelSpecification(
        model_name="Roborock S6 Pure",
        model_code=ROBOROCK_S6_PURE,
        fan_power_code=RoborockFanSpeedS6Pure,
        mop_mode_code=None,
        mop_intensity_code=None,
    ),
    ROBOROCK_S7_MAXV: ModelSpecification(
        model_name="Roborock S7 MaxV",
        model_code=ROBOROCK_S7_MAXV,
        fan_power_code=RoborockFanSpeedS7MaxV,
        mop_mode_code=RoborockMopModeS7,
        mop_intensity_code=RoborockMopIntensityS7,
    ),
    ROBOROCK_S7: ModelSpecification(
        model_name="Roborock S7",
        model_code=ROBOROCK_S7,
        fan_power_code=RoborockFanSpeedS7,
        mop_mode_code=RoborockMopModeS7,
        mop_intensity_code=RoborockMopIntensityS7,
    ),
    ROBOROCK_S8_PRO_ULTRA: ModelSpecification(
        model_name="Roborock S8 Pro Ultra",
        model_code=ROBOROCK_S8_PRO_ULTRA,
        fan_power_code=RoborockFanSpeedS7MaxV,
        mop_mode_code=RoborockMopModeS8ProUltra,
        mop_intensity_code=RoborockMopIntensityS7,
    ),
}
