import argparse
from ultralytics import YOLO
from ultralytics.solutions import SpeedEstimator
import cv2 as cv
import numpy as np
import os.path as path
from math import floor
from random import randint, choice, seed
from collections import defaultdict, deque
import PIL

class Leanbot: 
    id_counter = 0
    def __init__(self, center):
        self.id = self.id_counter
        self.center = center
        self.license_plate 
        self.path = deque([])

        counter += 1

    def add_path_point(self, x, y):
        self.path.append((x, y))
        if len(self.path) > 20:
            self.path.popleft() 

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

    cap = cv.VideoCapture(capture_device)
    fps = cap.get(cv.CAP_PROP_FPS)
    step = 1
    time_elapsed = 0

    leanbots = {}

    model = YOLO(model=model_path)  
    speed_obj = SpeedEstimator(
        model=model_path,
        fps=fps,
        max_hist=5,
        meter_per_pixel=0.0019,
    ) 
    warp_matrix = np.float32(np.load(args.warp_matrix_path))

    while True:
        ret, frame = cap.read()

        if not ret: break
        top_down = cv.warpPerspective(frame, warp_matrix, (frame.shape[1], frame.shape[0]))
        results = model.track(top_down, stream=True)

        for result in results:
            class_names = result.names
            for box in result.boxes:
                if box.conf[0] > 0.4:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    center = (x1 + ((x2 - x1)//2)), (y1 + ((y2 - y1)// 2))

                    cls = int(box.cls[0])
                    class_name = class_names[cls]

                    conf = float(box.conf[0])

                    colour = get_color(cls)

                    cv.rectangle(top_down, (x1, y1), (x2, y2), colour, 2)

                    cv.putText(top_down, f"{class_name} {conf:.2f}",
                                (x1, max(y1 - 10, 20)), cv.FONT_HERSHEY_SIMPLEX,
                                0.6, colour, 2) 

                    cv.circle(frame, radius=5, center=center, color=colour, thickness=-2)

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
    np.save(outfile, warp_matrix)
    

else:
    print("Invalid mode value (try: gather, train, run).")