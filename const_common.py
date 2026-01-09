"""
Common constants
"""

from types import MappingProxyType

# Numeric
FLOAT_INF = float("inf")
MAX_VEHICLES = 128  # set vehicle data size limit
MAX_SECONDS = 99999.0  # for lap or sector time limit
MAX_METERS = 999999.0  # for distance limit

MAX_FORECASTS = 5  # for weather forecast
MAX_FORECAST_MINUTES = 9999.0  # for weather forecast
ABS_ZERO_CELSIUS = -273.15  # absolute zero celsius

# Text
TEXT_PLACEHOLDER = "-"
TEXT_NA = "n/a"
TEXT_NOTAVAILABLE = "NOT AVAILABLE"
TEXT_NOLAPTIME = "-:--.---"
CRLF = "\r\n"

# Data set
EMPTY_DICT: MappingProxyType = MappingProxyType({})
DELTA_ZERO = (0.0, 0.0)  # pos, target
DELTA_DEFAULT = (DELTA_ZERO,)
POS_XY_ZERO = (0.0, 0.0)  # world origin position
POS_XYZ_ZERO = (0.0, 0.0, 0.0)  # world origin position
POS_XYZ_INF = (FLOAT_INF, FLOAT_INF, FLOAT_INF)  # infinite position
WHEELS_ZERO = (0.0, 0.0, 0.0, 0.0)  # FL, FR, RL, RR
WHEELS_NA = (-1.0, -1.0, -1.0, -1.0)  # FL, FR, RL, RR
WHEELS_DELTA_DEFAULT = (0.0, *WHEELS_ZERO)  # pos, target set
STINT_USAGE_DEFAULT = (-1.0, -1.0, -1.0, 0.0, 0)
REL_TIME_DEFAULT = (0.0, -1)  # relative time gap, player index
PITEST_DEFAULT = (
    0.0,  # min pit duration
    0.0,  # max pit duration
    0.0,  # relative refill (fuel)
    0.0,  # relative refill (virtual energy)
    0,  # stop go penalty state
)

# Type set
TYPE_NUMBER = (float, int)
TYPE_JSON = (dict, list)

# ID selector
ENERGY_TYPE_ID = (
    "FUEL",  # fuel
    "NRG",  # virtual energy
)
RACELENGTH_TYPE_ID = (
    "TIME",  # time-based race length
    "LAPS",  # laps-based race length
)
SECTOR_ABBR_ID = ("S1", "S2", "S3")  # sector abbreviation
PREV_SECTOR_INDEX = (2, 0, 1)  # select previous sector index with current index
GEAR_SEQUENCE = {  # max 9 in RF2
    -1: "R",
    0: "N",
    1: "1",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
}.get
COMPASS_BEARINGS = (
    (0, "N"),
    (22.5, "NE"),
    (67.5, "E"),
    (112.5, "SE"),
    (157.5, "S"),
    (202.5, "SW"),
    (247.5, "W"),
    (292.5, "NW"),
    (337.5, "N"),
)