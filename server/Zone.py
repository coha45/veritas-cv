from Enums import ZoneType
import json

class Zone:
    def __init__(self, p1, p2, name, zone_type, zone_direction=None):
        self.p1 = p1
        self.p2 = p2
        self.name = name
        self.type = zone_type
        self.color = self.get_color_from_zone(zone_type)
        self.zone_direction = zone_direction

    def point_overlaps(self, point):
        return point[0] > self.p1[0] and point[0] < self.p2[0] and point[1] > self.p1[1] and point[1] < self.p2[1]
    
    def __repr__(self):
        return f"Zone({self.p1}, {self.p2}, {self.name}, {self.type}, {self.color}, {self.zone_direction})"

    def to_dict(self):
        return {
            "p1" : self.p1,
            "p2" : self.p2,
            "name" : self.name,
            "type" : self.type.name,
            "color" : self.color,
            "zone_direction" : self.zone_direction if self.zone_direction else None
        }

    def expose(self):
        zone_dict = self.to_dict()
        return {
            "type" : zone_dict["type"],
            "name" : zone_dict["name"],
            "zone_direction" : zone_dict["zone_direction"]
        }
    
    @staticmethod
    def from_dict(zone_dict):
        return Zone(
            tuple(zone_dict["p1"]),
            tuple(zone_dict["p2"]),
            zone_dict["name"],
            ZoneType[zone_dict["type"]],
            zone_dict["zone_direction"]
        )

    @staticmethod
    def load_zones(src):
        with open(src, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [Zone.from_dict(zone) for zone in data]

    def get_color_from_zone(self, zone):
        match zone:
            case ZoneType.LEFT_LANE:
                return (255, 191, 0)
            case ZoneType.RIGHT_LANE:
                return (0, 255, 255)
            case ZoneType.PEDESTRIAN_LANE:
                return (0, 127, 255)
            case ZoneType.INTERSECTION:
                return (153, 102, 204)
            case ZoneType.RESTRICTED:
                return (255, 32, 82)