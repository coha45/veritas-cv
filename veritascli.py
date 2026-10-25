import argparse
from ultralytics import YOLO
import cv2 as cv
import os.path as path

parser = argparse.ArgumentParser(
    prog="veritas",
    description="Veritas CLI tool."
)

parser.add_argument("mode")
parser.add_argument("-o", "--outdir")
parser.add_argument("-e", "--epochs")
parser.add_argument("-t", "--time")
parser.add_argument("-cd", "--capture_device")
parser.add_argument("-i", "--interval")
parser.add_argument("-m", "--model")

args = parser.parse_args()

if args.mode == "gather":
    capture_device = int(args.capture_device) if args.capture_device.isnumeric() else 0
    outdir = args.outdir
    interval = 5
    time = args.time

    cap = cv.VideoCapture(0)
    fps = cap.get(cv.CAP_PROP_FPS)
    step = 1
    time_elapsed = 0
    while True:
        print(time_elapsed)
        ret, frame = cap.read()

        if not ret: break

        if time_elapsed % interval == 0:
            cv.imwrite(path.join(outdir, f"image{step}.png"), frame)

        cv.imshow("Gather Mode", frame)

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
