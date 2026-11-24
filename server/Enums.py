from enum import Enum, auto

class TrafficState(Enum):
    RED = auto()
    YELLOW = auto()
    GREEN = auto()

class ZoneType(Enum):
    LEFT_LANE = auto()
    RIGHT_LANE = auto()
    PEDESTRIAN_LANE = auto()
    INTERSECTION = auto()
    RESTRICTED = auto()