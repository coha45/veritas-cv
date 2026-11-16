import argparse
from ultralytics import YOLO
from ultralytics.solutions import SpeedEstimator
import cv2 as cv
import numpy as np
import os.path as path
from math import floor
from random import randint, choice, seed
from collections import defaultdict, deque
import math

# x-y tuples that need additional functionality/coherency
class Point:
    def __init__(self, x, y): 
        self.x = x
        self.y = y

    def get_dist(self, p2):
        return math.sqrt((self.y - p2.y)**2 + (self.x - p2.x)**2) 

class Leanbot: 
    id_counter = 0
    leanbots = []

    def __init__(self, x, y):
        leanbots.append(self)
        self.id = self.id_counter
        self.center = Point(x, y)
        self.license_plate = None
        self.path = deque([])

        id_counter += 1

    def add_path_point(self, x, y):
        self.path.append(Point(x, y))
        self.center = Point(x, y)
        if len(self.path) > 20:
            self.path.popleft() 

    def get_dist_from_last(self, pt):
        last_pt = self.path[-1]
        return last_pt.get_dist(pt)

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
parser.add_argument("-n", "--new-section")

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

    cap = cv.VideoCapture(source)
    fps = cap.get(cv.CAP_PROP_FPS)
    step = 1
    time_elapsed = 0

    leanbot_paths = defaultdict(lambda: [])

    model = YOLO(model=model_path)  
    speed_obj = SpeedEstimator(
        model=model_path,
        fps=fps,
        max_hist=50,
        meter_per_pixel=1,
    ) 
    warp_matrix = np.float32(np.load(args.warp_matrix_path))

    while True:
        ret, frame = cap.read()

        if not ret: break
        top_down = cv.warpPerspective(frame, warp_matrix, (640, 640))
        results = model.track(top_down, stream=True)

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
                        movement_path = leanbot_paths[id]
                        movement_path.append(centroid)

                        if len(movement_path) > 100:
                            movement_path.pop(0) 
                        
                        # Draw lines
                        points = np.hstack(movement_path).astype(np.int32).reshape(-1, 1, 2) 
                        cv.polylines(top_down, [points], isClosed=False, color=colour, thickness=2)

                    
        speed_obj_results = speed_obj.process(top_down)
        cv.imshow("Top View", top_down)

        if cv.waitKey(20) & 0xFF == ord('d'):
            break
    cap.release()
    cv.destroyAllWindows()

elif args.mode == "calibrate":
    capture_device = int(args.capture_device)
    outdir = args.outdir
    outfile = args.outfile
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
    np.save(outfile, warp_matrix)

else:
    print("Invalid mode value (try: gather, train, run, calibrate).")