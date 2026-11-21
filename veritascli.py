import argparse
import os
from ultralytics import YOLO
from ultralytics.solutions import SpeedEstimator
import cv2 as cv
import numpy as np
import os.path as path
from math import floor
from random import randint, choice, seed
from collections import defaultdict, deque
from collections.abc import MutableMapping
import math 
import datetime


def gen_key():
    ch = "abcdefghijklmnopqrstuvwxyz1234567890"
    return "".join([choice(ch) for i in range(randint(10,20))])

def get_color(cls_num):
    seed(cls_num)
    return tuple(randint(0,255) for _ in range(3))

def save_img(drawn, frame):
    rand_key = gen_key() 
    print(rand_key)
    cv.imwrite(path.join(outdir, f"image{rand_key}.png"), frame)
    width = int(cap.get(3))
    height = int(cap.get(4))
    return cv.rectangle(drawn, (0, 0), (width, height), (0, 255, 0), 5)

def get_dist(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return math.hypot(x2 - x1, y2 - y1)

def get_angle_in_radians(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return math.atan2((y2-y1), (x2-x1))

def get_angle_in_degrees(p1, p2):
    return math.degrees(get_angle_in_radians(p1, p2))

class DynamicDefaultDict(defaultdict):
    def __init__(self, factory):
        super().__init__(lambda : 0)
        self.factory = factory

    def __missing__(self, key):
        value = self.factory()
        self[key] = value
        return value


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
        self.speed = 0
        self.angle = 0
        self.speed_initialized = False
        self.angle_initialized = False

    def movement_info(self, dx, dy):
        last, current = self.last_current
        print(f"Last: {last}, Current: {current}")
        print(f"dx; {dx}, dy: {y}")
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


class Zone:
    def __init__(self, p1, p2, name, zone_type):
        self.p1 = tuple(map(int, p1.tolist()))
        self.p2 = tuple(map(int, p2.tolist()))
        self.name = name
        self.type = zone_type
        self.color = get_color(randint(1, 200))

    def point_overlaps(self, point):
        return point[0] > self.p1[0] and point[0] < self.p2[0] and point[1] > self.p1[1] and point[1] < self.p2[1]
    
    def __repr__(self):
        return f"Zone({self.p1}, {self.p2}, {self.name}, {self.type}, {self.color})"


def get_points_from_file(dir):
    if not os.path.exists(dir): return None

    dir_items = os.listdir(dir)
    items = {}

    for item in dir_items:
        item_path = os.path.join(dir, item)
        if item.endswith(".npy"): 
            filename = item.split(".")[0]
            zone_type = os.path.basename(os.path.normpath(dir))
            p1, p2 = np.load(item_path)
            items[filename] = Zone(p1, p2, filename, zone_type)
        elif os.path.exists(os.path.join(dir, item)):
            items[item] = get_points_from_file(item_path)
    return items

def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str ='.') -> MutableMapping:
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def draw_direction(frame, angle, x1, y1, length=25, color=(255, 0, 0), thickness=2):
    print(f"Angle degrees: {angle}")

    x2 = int(x1 + length*math.cos(angle))
    y2 = int(y1 + length*math.sin(angle))

    cv.arrowedLine(frame, (x1, y1), (x2, y2), color, thickness)

    return frame

parser = argparse.ArgumentParser(
    prog="veritas",
    description="Veritas CLI tool."
)

parser.add_argument("mode")
parser.add_argument("-o", "--outfile")
parser.add_argument("-od", "--outdir")
parser.add_argument("-wm", "--warp_matrix_path")
parser.add_argument("-e", "--epochs")
parser.add_argument("-t", "--time", default=30)
parser.add_argument("-cd", "--capture_device", default=0)
parser.add_argument("-i", "--interval", default=5)
parser.add_argument("-m", "--model")
parser.add_argument("-s", "--source")
parser.add_argument("-rs", "--road_sections_path")

args = parser.parse_args()

if args.mode == "gather":
    print("READY:GATHER", flush=True)
    capture_device = int(args.capture_device)
    outdir = args.outdir
    interval = int(args.interval)
    run_time = int(args.time)

    cap = cv.VideoCapture(capture_device)
    fps = cap.get(cv.CAP_PROP_FPS)
    step = 1
    time_elapsed = 0

    while True:
        ret, frame = cap.read()

        if not ret: break

        cp = np.copy(frame)
        drawn = cv.putText(cp, f"Elapsed Time: {floor(time_elapsed)}s\nStep: {step}\n", (30, 30), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255 , 0), 2)
        if interval != 0:
            if time_elapsed % interval == 0:
                drawn = save_img(drawn, frame)

        key = cv.waitKey(20) 

        if key & 0xFF == ord('d') or time_elapsed > run_time:
            break
        elif key == 32:
            if interval == 0:
                drawn = save_img(drawn, frame)
                    
        cv.imshow("Gather Mode", drawn)
        

        step +=1
        time_elapsed = step/fps

    cap.release()
    cv.destroyAllWindows()
elif args.mode == "train":
    model = YOLO(args.model)


    results = model.train()
elif args.mode == "run":
    print("READY:RUN", flush=True)
    UPDATE_INTERVAL = 15
    capture_device = int(args.capture_device)
    outdir = args.outdir
    interval = int(args.interval)
    time = int(args.time)
    model_path = args.model
    source = args.source
    warp_matrix_path = args.warp_matrix_path
    road_sections = args.road_sections_path

    cap = cv.VideoCapture(capture_device)
    fps = cap.get(cv.CAP_PROP_FPS)
    time_elapsed = 0
    step = 0

    leanbots = defaultdict(lambda: Leanbot(0 ,0))

    # Process Zones
    zones = get_points_from_file(road_sections)
    
    model = YOLO(model=model_path) 
    if warp_matrix_path is not None: 
        warp_matrix = np.float32(np.load(args.warp_matrix_path))
    else:
        warp_matrix = None

    while True:
        ret, frame = cap.read()

        if not ret: break

        time_elapsed = step/fps

        if warp_matrix is None:
            top_down = frame
        else:
            top_down = cv.warpPerspective(frame, warp_matrix, (640, 640))
        results = model.track(top_down, stream=True, persist=True, tracker="bytetrack.yaml")

        for result in results:
            # Get Ids and convert to list
            if result.boxes is None or result.boxes.id is None: continue
            ids = result.boxes.id.cpu().tolist()
            class_names = result.names
            for box, id in zip(result.boxes, ids):
                if box.conf[0] > 0.4:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    centroid = (x1 + ((x2 - x1)//2)), (y1 + ((y2 - y1)// 2))

                    cls = int(box.cls[0])
                    class_name = class_names[cls]

                    conf = float(box.conf[0])

                    colour = get_color(cls)
                    if class_name == "Leanbot":
                        if len(leanbots[id].violations) >= 1:
                            colour = (0, 0, 255)
                        
                    cv.rectangle(top_down, (x1, y1), (x2, y2), colour, 2)

                    cv.putText(top_down, f"{class_name} {conf:.2f}",
                                (x1, max(y1 - 10, 20)), cv.FONT_HERSHEY_SIMPLEX,
                                0.6, colour, 2) 

                    # Draw movement path if result object is a leanbot.                    
                    if class_name == "Leanbot":
                        cur_leanbot = leanbots[id]
                        x, y = centroid

                        # Update Space-Time
                        if step % UPDATE_INTERVAL == 0:
                            cur_leanbot.update_last(x, y, time_elapsed)

                        # Path
                        speed, _ = cur_leanbot.get_velocity_vector()
                        angle = cur_leanbot.get_avg_angle_in_radians()
                        print(f"Speed: {speed}")


                        # Draw lines
                        points = cur_leanbot.get_polylines(centroid) 
                        cv.polylines(top_down, [points], isClosed=False, color=colour, thickness=2)


                        if angle is not None:
                            top_down = draw_direction(top_down, angle, x, y)
                            cv.putText(top_down, f"Angle: {angle:0.2f}", (x1, max(y - 35, 70)),
                                   cv.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2)

                        cv.putText(top_down, f"Speed: {speed:0.2f}cm/s", (x1, max(y1 - 25, 50)),
                                   cv.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2)

                        print(cur_leanbot.violations)
                        
                        if speed > 40:
                            cur_leanbot.add_violation("Speeding")
                    
                        for zone in flatten_dict(zones).values():
                            if zone.point_overlaps(centroid):
                                cur_leanbot.current_zone = zone
                        if cur_leanbot.current_zone is not None:
                            if cur_leanbot.current_zone.type == "restricted":
                                print(f"In zone {cur_leanbot.current_zone.name}")

        for zone in list(flatten_dict(zones).values()):
            cv.rectangle(top_down, zone.p1, zone.p2, zone.color, 2)

        cv.imshow("Top View", top_down)

        if cv.waitKey(20) & 0xFF == ord('d'):
            break

        step += 1

    cap.release()
    cv.destroyAllWindows()

elif args.mode == "calibrate":
    filename = input("Perspective Warp Name: ") + ".npy"
    capture_device = int(args.capture_device)
    outdir = args.outdir
    outfile = os.path.join(outdir, filename)
    source = args.source

    src = []
    dst = []
    points = []

    def add_point(event, x, y, flags, params):
        if event == cv.EVENT_LBUTTONDOWN:
            points.append([x, y])

    cap = cv.VideoCapture(capture_device)
    while True:
        if len(points) >= 4: break
        ret, frame = cap.read()

        if not ret: break

        for i, (x, y) in enumerate(points):
            cv.circle(frame, radius=5, center=(x, y), color=(255, 0, 0), thickness=-1)
            cv.putText(frame, f"p{i+1}", (x, y), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv.imshow("Calibration", frame)
        cv.setMouseCallback("Calibration", add_point)

        if cv.waitKey(20) & 0xFF == ord('d'):
            break

    cap.release()
    cv.destroyAllWindows()

    print("Source Points:", points)
    src = np.float32(points) 
    points = []


    while True:
        if len(points) >= 4: break
        top_down = cv.imread("./assets/topdown.png")
        top_down = cv.resize(top_down, (640, 640))

        for i, (x, y) in enumerate(points): 
            cv.circle(top_down, center=(x, y), radius=5, thickness=-1, color=(255, 33, 0))
            cv.putText(top_down, f"p{i+1}", (x, y), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv.imshow("Top Down Calibration", top_down)
        cv.setMouseCallback("Top Down Calibration", add_point)

        cv.waitKey(1)

    dst = np.float32(points)    
    print("Destination Points:", points)

    warp_matrix = cv.getPerspectiveTransform(src, dst)

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    np.save(outfile, warp_matrix)

elif args.mode == "divide": 
    filename = input("New Section Title: ") + ".npy"
    capture_device = int(args.capture_device)
    outdir = args.outdir
    outfile = os.path.join(outdir, filename)
    source = args.source

    src = []
    dst = []
    points = []

    def add_point(event, x, y, flags, params):
        if event == cv.EVENT_LBUTTONDOWN:
            points.append([x, y])

    while True:
        if len(points) >= 2: break
        top_down = cv.imread("./assets/topdown.png")
        top_down = cv.resize(top_down, (640, 640))

        for i, (x, y) in enumerate(points): 
            cv.circle(top_down, center=(x, y), radius=5, thickness=-1, color=(255, 33, 0))
            cv.putText(top_down, f"p{i+1}", (x, y), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv.imshow("New Section", top_down)
        cv.setMouseCallback("New Section", add_point)

        cv.waitKey(1)

    new_section = np.float32(points)
    print("New Section Created:", points)

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    np.save(outfile, new_section)

else:
    print("Invalid mode value (try: gather, train, run, calibrate).")