# Total time in seconds consumables have before Roborock recommends replacing
MAIN_BRUSH_REPLACE_TIME = 1080000
SIDE_BRUSH_REPLACE_TIME = 720000
FILTER_REPLACE_TIME = 540000
SENSOR_DIRTY_REPLACE_TIME = 108000


ROBOROCK_V1 = "ROBOROCK.vacuum.v1"
ROBOROCK_S4 = "roborock.vacuum.s4"
ROBOROCK_S4_MAX = "roborock.vacuum.a19"
ROBOROCK_S5 = "roborock.vacuum.s5"
ROBOROCK_S5_MAX = "roborock.vacuum.s5e"
ROBOROCK_S6 = "roborock.vacuum.s6"
ROBOROCK_T6 = "roborock.vacuum.t6"  # cn s6
ROBOROCK_E4 = "roborock.vacuum.a01"
ROBOROCK_S6_PURE = "roborock.vacuum.a08"
ROBOROCK_T7 = "roborock.vacuum.a11"  # cn s7
ROBOROCK_T7S = "roborock.vacuum.a14"
ROBOROCK_T7SPLUS = "roborock.vacuum.a23"
ROBOROCK_S7_MAXV = "roborock.vacuum.a27"
ROBOROCK_S7_PRO_ULTRA = "roborock.vacuum.a62"
ROBOROCK_Q5 = "roborock.vacuum.a34"
ROBOROCK_Q7 = "roborock.vacuum.a37"  # CHECK THIS
ROBOROCK_Q7_MAX = "roborock.vacuum.a38"
ROBOROCK_Q7PLUS = "roborock.vacuum.a40"
ROBOROCK_G10S = "roborock.vacuum.a46"
ROBOROCK_G10 = "roborock.vacuum.a29"
ROBOROCK_S7 = "roborock.vacuum.a15"
ROBOROCK_S6_MAXV = "roborock.vacuum.a10"
ROBOROCK_E2 = "roborock.vacuum.e2"
ROBOROCK_1S = "roborock.vacuum.m1s"
ROBOROCK_C1 = "roborock.vacuum.c1"
ROBOROCK_S8_PRO_ULTRA = "roborock.vacuum.a61"  # CHECK THIS
ROBOROCK_S8 = "roborock.vacuum.a60"  # CHECK THIS
ROBOROCK_WILD = "roborock.vacuum.*"  # wildcard

SUPPORTED_VACUUMS = (
    [  # These are the devices that show up when you add a device - more could be supported and just not show up
        ROBOROCK_G10,
        ROBOROCK_Q5,
        ROBOROCK_Q7,
        ROBOROCK_Q7_MAX,
        ROBOROCK_S4,
        ROBOROCK_S5_MAX,
        ROBOROCK_S6,
        ROBOROCK_S6_MAXV,
        ROBOROCK_S6_PURE,
        ROBOROCK_S7_MAXV,
        ROBOROCK_S8_PRO_ULTRA,
        ROBOROCK_S8,
        ROBOROCK_S4_MAX,
        ROBOROCK_S7,
    ]
)
