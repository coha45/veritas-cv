from enum import Enum, auto

class TrafficState(Enum):
    RED = auto()
    GREEN = auto()

class ZoneType(Enum):
    LEFT_LANE = auto()
    RIGHT_LANE = auto()
    PEDESTRIAN_LANE = auto()
    INTERSECTION = auto()
    RESTRICTED = auto()

class ViolationType(Enum):
    SPEEDING = auto()
    FAILURE_TO_YIELD = auto()
    WRONG_WAY = auto()
    RUNNING_RED_LIGHT = auto()
    BLOCKING_ROAD = auto()
    RESTRICTED_AREA = auto() 

