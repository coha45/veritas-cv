import argparse
from ultralytics import YOLO
import cv2 as cv
import numpy as np
import os.path as path
from math import floor

def validate_int(value):
    try:
        n = int(value)
        return n
    except TypeError:
        raise argparse.ArgumentTypeError("Invalid Value Passed")

parser = argparse.ArgumentParser(
    prog="veritas",
    description="Veritas CLI tool."
)

parser.add_argument("mode")
parser.add_argument("-o", "--outdir")
parser.add_argument("-e", "--epochs")
parser.add_argument("-t", "--time", default=30)
parser.add_argument("-cd", "--capture_device", default=0)
parser.add_argument("-i", "--interval", default=5)
parser.add_argument("-m", "--model")

args = parser.parse_args()

if args.mode == "gather":
    capture_device = args.capture_device
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
        if time_elapsed % interval == 0:
            cv.imwrite(path.join(outdir, f"image{step}.png"), frame)
            width = int(cap.get(3))
            height = int(cap.get(4))
            drawn = cv.rectangle(drawn, (0, 0), (width, height), (0, 255, 0), 5)

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
    pass
else:
    print("Invalid mode value (try: gather, train, run).")