import argparse
import cv2 as cv

parser = argparse.ArgumentParser(
    prog="veritas",
    description="Veritas CLI tool."
)

parser.add_argument("mode")
parser.add_argument("-o", "--outdir")
parser.add_argument("-e", "--epochs")
parser.add_argument("-t", "--time")
parser.add_argument("-cd", "--capture-device")
parser.add_argument("-i", "--interval")
parser.add_argument("-m", "--model")

args = parser.parse_args()

if args.mode == "gather":
    capture_device = args.cd if args.cd else 0
    cap = cv.VideoCapture(capture_device)

    while True:
        ret, frame = cap.read()

        cv.imshow(frame)

        if cv.waitKey(20) == 0xFF & ord('d'):
            break

    cap.release()
    cv.destroyAllWindows()
elif args.mode == "train":
    pass
elif args.mode == "run":
    pass
else:
    print("Invalid mode value (try: gather, train, run).")
