from collections import deque
import math
import numpy as np
from Zone import Zone

class Leanbot:
    CM_PER_PIXEL = 0.1905
    MAX_CM_THRESH = 500.0 # Implausible speed 
    SPEED_SMOOTHING_FACTOR = 0.05
    ANGLE_SMOOTHING_FACTOR = 0.05
    MIN_DIRECTION_DISTANCE = 3.0

    def __init__(self, x, y):
        self.last_current = deque([(x, y, 0)], maxlen=2)
        self.violations = set()
        self.movement_path = deque(maxlen=50)
        self.license_plate = None
        self.current_zone = None
        self.time_since_entered = 0
        self.time_entered = 0
        self.speed = 0
        self.angle = 0
        self.speed_initialized = False
        self.angle_initialized = False

    def __repr__(self):
        return(f"Leanbot({self.last_current}, {self.violations}, {self.license_plate}, {self.time_since_entered}, {self.speed}, {self.angle})")

    def to_dict(self):
        return {
            "last_current" : tuple(self.last_current),
            "violations" : tuple(self.violations),
            "movement_path" : list(self.movement_path),
            "license_plate" : self.license_plate,
            "current_zone" : None if self.current_zone is None else self.current_zone.to_dict(),
            "time_since_entered" : self.time_since_entered,
            "time_entered" : self.time_entered,
            "speed" : self.speed,
            "angle" : self.angle,
            "speed_initialized" : self.speed_initialized,
            "angle_initialized" : self.angle_initialized
        }

    @staticmethod
    def from_dict(leanbot_dict):
        new_leanbot = Leanbot(0, 0)
        new_leanbot.last_current = deque(leanbot_dict["last_current"], maxlen=2)
        new_leanbot.violations = set(leanbot_dict["violations"])
        new_leanbot.movement_path = deque(leanbot_dict["movement_path"], maxlen=50)
        new_leanbot.license_plate = leanbot_dict["license_plate"]
        new_leanbot.current_zone = Zone.from_dict(leanbot_dict["current_zone"]) if leanbot_dict["current_zone"] is not None else None
        new_leanbot.time_since_entered = leanbot_dict["time_since_entered"]
        new_leanbot.time_entered = leanbot_dict["time_entered"]
        new_leanbot.speed = leanbot_dict["speed"]
        new_leanbot.angle = leanbot_dict["angle"]
        new_leanbot.speed_initialized = leanbot_dict["speed_initialized"]
        new_leanbot.angle_initialized = leanbot_dict["angle_initialized"]
        return new_leanbot

    def movement_info(self, dx, dy):
        last, current = self.last_current
        print(f"Last: {last}, Current: {current}")
        print(f"dx; {dx}, dy: {dy}")
        print(f"Speed: {self.speed}, Angle: {self.angle}")

    def get_velocity_vector(self):
        if len(self.last_current) < 2: return (0.0, self.angle)

        x1, y1, timestamp = self.last_current[0]
        x2, y2, timestamp2 = self.last_current[1]

        dx = x2 - x1
        dy = y2 - y1
        distance = math.hypot(dx, dy)
        self.angle = math.atan2(dy, dx)
        
        if distance < 2: return (0.0, self.angle)
        distance_cm = distance * self.CM_PER_PIXEL

        time_elapsed = timestamp2 - timestamp
        if time_elapsed <= 0: return (0.0, 0.0)

        raw_speed = distance_cm/time_elapsed

        if raw_speed > self.MAX_CM_THRESH:
            return (self.speed, self.angle)
        
        if not self.speed_initialized:
            self.speed = raw_speed
        else:
            alpha = self.SMOOTHING_FACTOR
            self.speed = (alpha * raw_speed + (1 - alpha) * self.speed)

        self.movement_info(dx, dy)

        return (self.speed, self.angle)


    def get_avg_angle_in_radians(self, hist=25):
        movement_path = list(self.movement_path)

        if len(movement_path) < 2: 
            self.angle = None 
            return None

        points = movement_path[-hist-1:]

        sin_sum = 0.0
        cos_sum = 0.0
        count = 0

        for i in range(1, len(points)):
            x1, y1 = points[i-1]
            x2, y2 = points[i]

            dx = x2 - x1
            dy = y2 - y1

            if math.hypot(dx, dy) < self.MIN_DIRECTION_DISTANCE:
                continue

            angle = math.atan2(dy, dx)

            sin_sum += math.sin(angle)
            cos_sum += math.cos(angle)

            count += 1

        if count == 0:
            self.angle = None
            return self.angle

        raw_angle = math.atan2(sin_sum, cos_sum)
        if not self.angle_initialized:
            self.angle = raw_angle
        else:
            alpha = self.ANGLE_SMOOTHING_FACTOR
            self.angle = (alpha * raw_angle + (1 - alpha) * self.angle)

        return self.angle              
            
    def update_last(self, x, y, timestamp): 
        self.last_current.append((x, y, timestamp))

    def get_polylines(self, point):
        self.movement_path.append(point)
        return np.hstack(self.movement_path).astype(np.int32).reshape(-1, 1, 2) 

    def add_violation(self, violation_type):
        self.violations.add(violation_type)

    def check_current_zone(self, zones, point, time_elapsed):
        if self.current_zone is not None:
            if self.current_zone.point_overlaps(point):
                self.time_since_entered = time_elapsed - self.time_entered
                return True
            else:
                self.current_zone = None
                return self.check_current_zone(zones, point, time_elapsed)

        for zone in zones:
            if zone.point_overlaps(point):
                self.time_entered = time_elapsed
                self.time_since_entered = 0
                self.current_zone = zone
                return True

        return False

        