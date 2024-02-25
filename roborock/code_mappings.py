from __future__ import annotations

import logging
from enum import Enum, IntEnum

_LOGGER = logging.getLogger(__name__)


class RoborockEnum(IntEnum):
    """Roborock Enum for codes with int values"""

    @property
    def name(self) -> str:
        return super().name.lower()

    @classmethod
    def _missing_(cls: type[RoborockEnum], key) -> RoborockEnum:
        if hasattr(cls, "unknown"):
            _LOGGER.warning(f"Missing {cls.__name__} code: {key} - defaulting to 'unknown'")
            return cls.unknown  # type: ignore
        default_value = next(item for item in cls)
        _LOGGER.warning(f"Missing {cls.__name__} code: {key} - defaulting to {default_value}")
        return default_value

    @classmethod
    def as_dict(cls: type[RoborockEnum]):
        return {i.name: i.value for i in cls if i.name != "missing"}

    @classmethod
    def as_enum_dict(cls: type[RoborockEnum]):
        return {i.value: i for i in cls if i.name != "missing"}

    @classmethod
    def values(cls: type[RoborockEnum]) -> list[int]:
        return list(cls.as_dict().values())

    @classmethod
    def keys(cls: type[RoborockEnum]) -> list[str]:
        return list(cls.as_dict().keys())

    @classmethod
    def items(cls: type[RoborockEnum]):
        return cls.as_dict().items()


class RoborockStateCode(RoborockEnum):
    unknown = 0
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
    in_call = 28
    mapping = 29
    egg_attack = 30
    charging_complete = 100
    device_offline = 101
    locked = 103
    air_drying_stopping = 202
    robot_status_mopping = 6301
    clean_mop_cleaning = 6302
    clean_mop_mopping = 6303
    segment_mopping = 6304
    segment_clean_mop_cleaning = 6305
    segment_clean_mop_mopping = 6306
    zoned_mopping = 6307
    zoned_clean_mop_cleaning = 6308
    zoned_clean_mop_mopping = 6309
    back_to_dock_washing_duster = 6310


class RoborockDyadStateCode(RoborockEnum):
    unknown = -999
    fetching = -998  # Obtaining Status
    fetch_failed = -997  # Failed to obtain device status. Try again later.
    updating = -996
    washing = 1
    ready = 2
    charging = 3
    mop_washing = 4
    self_clean_cleaning = 5
    self_clean_deep_cleaning = 6
    self_clean_rinsing = 7
    self_clean_dehydrating = 8
    drying = 10
    ventilating = 11  # drying
    reserving = 12
    mop_washing_paused = 13
    dusting_mode = 14


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
    strainer_error = 10  # Filter is wet or blocked
    compass_error = 11  # Strong magnetic field detected
    low_battery = 12
    charging_error = 13
    battery_error = 14
    wall_sensor_dirty = 15
    robot_tilted = 16
    side_brush_error = 17
    fan_error = 18
    dock = 19  # Dock not connected to power
    vertical_bumper_pressed = 21
    dock_locator_error = 22
    return_to_dock_fail = 23
    nogo_zone_detected = 24
    visual_sensor = 25  # Camera error
    light_touch = 26  # Wall sensor error
    vibrarise_jammed = 27
    robot_on_carpet = 28
    filter_blocked = 29
    invisible_wall_detected = 30
    cannot_cross_carpet = 31
    internal_error = 32
    collect_dust_error_3 = 34  # Clean auto-empty dock
    collect_dust_error_4 = 35  # Auto empty dock voltage error
    mopping_roller_1 = 36  # Wash roller may be jammed
    mopping_roller_error_2 = 37  # wash roller not lowered properly
    clear_water_box_hoare = 38  # Check the clean water tank
    dirty_water_box_hoare = 39  # Check the dirty water tank
    sink_strainer_hoare = 40  # Reinstall the water filter
    clear_water_box_exception = 41  # Clean water tank empty
    clear_brush_exception = 42  # Check that the water filter has been correctly installed
    clear_brush_exception_2 = 43  # Positioning button error
    filter_screen_exception = 44  # Clean the dock water filter
    mopping_roller_2 = 45  # Wash roller may be jammed
    temperature_protection = 51  # Unit temperature protection


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
    custom = 106
    max_plus = 108


class RoborockFanSpeedS6Pure(RoborockFanPowerCode):
    gentle = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106


class RoborockFanSpeedQ7Max(RoborockFanPowerCode):
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104


class RoborockFanSpeedP10(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106
    max_plus = 108


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
    custom = 302


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


class RoborockMopIntensityP10(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207


class RoborockMopIntensityS5Max(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207


class RoborockMopIntensityS6MaxV(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207


class RoborockDockErrorCode(RoborockEnum):
    """Describes the error code of the dock."""

    ok = 0
    duct_blockage = 34
    water_empty = 38
    waste_water_tank_full = 39
    dirty_tank_latch_open = 44
    no_dustbin = 46
    cleaning_tank_full_or_blocked = 53


class RoborockDockTypeCode(RoborockEnum):
    unknown = -9999
    no_dock = 0
    auto_empty_dock = 1
    empty_wash_fill_dock = 3
    auto_empty_dock_pure = 5
    s7_max_ultra_dock = 6
    s8_dock = 7
    p10_dock = 8


class RoborockDockDustCollectionModeCode(RoborockEnum):
    """Describes the dust collection mode of the vacuum cleaner."""

    # TODO: Get the correct values for various different docks
    unknown = -9999
    smart = 0
    light = 1
    balanced = 2
    max = 4


class RoborockDockWashTowelModeCode(RoborockEnum):
    """Describes the wash towel mode of the vacuum cleaner."""

    # TODO: Get the correct values for various different docks
    unknown = -9999
    light = 0
    balanced = 1
    deep = 2


class RoborockCategory(Enum):
    """Describes the category of the device."""

    WET_DRY_VAC = "roborock.wetdryvac"
    VACUUM = "robot.vacuum.cleaner"
    WASHING_MACHINE = "roborock.wm"
    UNKNOWN = "UNKNOWN"

    def __missing__(self, key):
        _LOGGER.warning("Missing key %s from category", key)
        return RoborockCategory.UNKNOWN
