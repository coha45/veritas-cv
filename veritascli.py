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
import math


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
    return math.sqrt(abs((y2 - y1) + (x2 - x1)))

class DynamicDefaultDict(defaultdict):
    def __init__(self, factory):
        super().__init__(lambda : 0)
        self.factory = factory

    def __missing__(self, key):
        value = self.factory()
        self[key] = value
        return value


class Leanbot:
    METERS_PER_PIXEL = 1

    def __init__(self, x, y):
        self.last_current = deque([(x, y)], maxlen=2)
        self.violator = False
        self.movement_path = deque(maxlen=50)

    def get_speed_in_meters(self, time_elapsed):
        if len(self.last_current) < 2: return 0
        p1, p2 = self.last_current
        distance = get_dist(p1, p2)
        print(f"Distance between {p1} and {p2}: {distance}")
        return (distance/max(1, time_elapsed)) * self.METERS_PER_PIXEL

    def update_last(self, x, y): 
        self.last_current.append((x, y))


    
class Zone:
    def __init__(self, p1, p2):
        self.p1 = tuple(map(int, p1.tolist()))
        self.p2 = tuple(map(int, p2.tolist()))
        print(self.p1)
        self.color = get_color(randint(1, 200))

    def point_overlaps(self, point):
        return point[0] > self.p1[0] and point[0] < self.p2[0] and point[1] > self.p1[1] and point[1] < self.p2[1]

    def __repr__(self):
        return f"Zone({self.p1}, {self.p2})"

def get_points_from_file(dir):
    if not os.path.exists(dir): return None

    dir_items = os.listdir(dir)
    items = {}

    for item in dir_items:
        item_path = os.path.join(dir, item)
        if item.endswith(".npy"): 
            filename = item.split(".")[0]
            p1, p2 = np.load(item_path)
            items[filename] = Zone(p1, p2)
        elif os.path.exists(os.path.join(dir, item)):
            items[item] = get_points_from_file(item_path)
    return items

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
    time = int(args.time)

    cap = cv.VideoCapture(capture_device)
    fps = cap.get(cv.CAP_PROP_FPS)
    step = 1
    time_elapsed = 0

    while True:
        ret, frame = cap.read()
        cp = np.copy(frame)

        if not ret: break

        drawn = cv.putText(cp, f"Elapsed Time: {floor(time_elapsed)}s\nStep: {step}\n", (30, 30), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255 , 0), 2)
        if interval == 0:
            if cv.waitKey(20) == 32:
                drawn = save_img(drawn, frame)
        elif time_elapsed % interval == 0:
            drawn = save_img(drawn, frame)

        cv.imshow("Gather Mode", drawn)
        if cv.waitKey(20) & 0xFF == ord('d') or time_elapsed > time:
            break

        step +=1
        time_elapsed = step/fps

    cap.release()
    cv.destroyAllWindows()
elif args.mode == "train":
    model = YOLO(args.model)


    results = model.train()
elif args.mode == "run":
    print("READY:RUN", flush=True)
    capture_device = int(args.capture_device)
    outdir = args.outdir
    interval = int(args.interval)
    time = int(args.time)
    model_path = args.model
    source = args.source
    warp_matrix_path = args.warp_matrix_path
    road_sections = args.road_sections_path

    cap = cv.VideoCapture(source)
    fps = cap.get(cv.CAP_PROP_FPS)
    step = 1
    time_elapsed = 0
    speed_update_interval = 1

    leanbots = defaultdict(lambda: Leanbot(0 ,0))

    # Process Zones
    zones = get_points_from_file(road_sections)
    speed_detection_zones = zones["speeding"]
    restricted = zones["restricted"]
    road_zones = zones["road"]
    
    model = YOLO(model=model_path)  
    warp_matrix = np.float32(np.load(args.warp_matrix_path))


    while True:
        ret, frame = cap.read()

        if not ret: break
        top_down = cv.warpPerspective(frame, warp_matrix, (640, 640))
        results = model.track(top_down, stream=True, tracker="bytetrack.yaml")

        time_elapsed = step//fps

        # for name, zone in zip(road_zones.keys(), road_zones.values()):
        #   cv.rectangle(top_down, zone.p1, zone.p2, zone.color, 2)

        for result in results:
            # Get Ids and convert to list
            if result.boxes is None or result.boxes.id is None: continue
            ids = result.boxes.id.cpu().tolist()
            class_names = result.names
            for box, id in zip(result.boxes, ids):
                if box.conf[0] > 0.6:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    centroid = (x1 + ((x2 - x1)//2)), (y1 + ((y2 - y1)// 2))

                    cls = int(box.cls[0])
                    class_name = class_names[cls]

                    conf = float(box.conf[0])

                    colour = get_color(cls)

                    cv.rectangle(top_down, (x1, y1), (x2, y2), colour, 2)

                    cv.putText(top_down, f"{class_name} {conf:.2f}",
                                (x1, max(y1 - 10, 20)), cv.FONT_HERSHEY_SIMPLEX,
                                0.6, colour, 2) 

                    # Draw movement path if result object is a leanbot.                    
                    if class_name == "Leanbot":
                        cur_leanbot = leanbots[id]
                        x, y = centroid
                        if step % speed_update_interval == 0:
                            cur_leanbot.update_last(x, y)
                        movement_path = leanbots[id].movement_path
                        movement_path.append(centroid)

                        if len(movement_path) > 100:
                            movement_path.pop(0) 
                        
                        # Draw lines
                        points = np.hstack(movement_path).astype(np.int32).reshape(-1, 1, 2) 
                        cv.polylines(top_down, [points], isClosed=False, color=colour, thickness=2)

                        print(cur_leanbot.get_speed_in_meters(time_elapsed))

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

    cap = cv.VideoCapture(source)
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