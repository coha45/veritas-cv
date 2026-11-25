import argparse
import os
from ultralytics import YOLO
import cv2 as cv
import numpy as np
from math import floor
from collections import defaultdict
import math 
import pyautogui 
import json
import zmq

from utils import *

from Leanbot import Leanbot
from Zone import Zone
from Enums import ZoneType, TrafficState

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
                drawn = save_img(outdir, cap, drawn, frame)

        key = cv.waitKey(20) 

        if key & 0xFF == ord('d') or time_elapsed > run_time:
            break
        elif key == 32:
            if interval == 0:
                drawn = save_img(outdir, cap, drawn, frame)
                    
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

    # Server Communication
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.setsockopt(zmq.IDENTITY, b"TOPDOWN")
    socket.connect("tcp://127.0.0.1:5555")

    video_socket = context.socket(zmq.DEALER)
    video_socket.setsockopt(zmq.IDENTITY, b"VIDEO_TOPDOWN")
    video_socket.connect("tcp://127.0.0.1:5555")

    # Process Zones
    zones = Zone.load_zones(road_sections)
    
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
        results = model.track(top_down, verbose=False, stream=True, persist=True, tracker="bytetrack.yaml")

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
                    
        for zone in zones:
            p1 = zone.p1
            p2 = zone.p2
            x1, y1 = p1
            x2, y2 = p2
            angle = zone.zone_direction
            x, y = (x1 + ((x2 - x1)//2), y1 + ((y2 - y1)//2))
            color = zone.color
            top_down = draw_center_text(top_down, p1, p2, zone.name, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1, color)
            if angle is not None:
                angle = math.radians(angle)
                top_down = draw_direction(top_down, angle, x, y, 50, color, 3)

            cv.rectangle(top_down, p1, p2, color, 2)

        cv.imshow("Top View", top_down)

        leanbot_dict = {
            key : leanbot.to_dict()
            for key, leanbot in dict(leanbots).items() 
        }

        socket.send_json(leanbot_dict)
        publish_frame(video_socket, top_down, b"VIDEO_TOPDOWN", 1)

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
    filename = pyautogui.prompt("Filename") 
    filename = "output.json" if filename is None else filename+".json"
    outdir = args.outdir
    outfile = os.path.join(outdir, filename)
    source = args.source

    recs = []

    current_point = None
    mouse_pos = None

    def prompt_zone_direction():
        while True:
            zone_direction = pyautogui.prompt("Zone Direction in Degrees")
            if zone_direction is None: return None

            try:
                l = int(zone_direction)
            except:
                continue

            return l

    def handle_point(event, x, y, flags, params):
        global current_point
        global mouse_pos

        if event == cv.EVENT_LBUTTONDOWN:
            if current_point is None:
                current_point = (x, y)
            else:
                rectangle_pts = (current_point, (x, y))

                zone_direction = None
                zone_name = pyautogui.prompt("Name of created zone:")  
                if zone_name is None or zone_name in [z.name for z in recs]:
                    current_point = None  
                    return
                zone_name = zone_name.strip()

                zone_type = pyautogui.confirm(
                    "Select a Zone type: ", 
                    buttons=[zone.name for zone in ZoneType]
                ) 
                if zone_type is None: 
                    current_point = None
                    return

                zone_type = ZoneType[zone_type]
                if zone_type == ZoneType.LEFT_LANE or zone_type == ZoneType.RIGHT_LANE: 
                    zone_direction = prompt_zone_direction()
                    if zone_direction is None: # Returns None as a result of cancellation
                        current_point = None
                        return


                print(f"Zone Name: {zone_name}")
                print(f"Zone Type: {zone_type}")

                if zone_direction is not None:
                    print(f"Zone Direction: {zone_direction}")

                zone = Zone(rectangle_pts[0], rectangle_pts[1], zone_name, zone_type, zone_direction)

                recs.append(zone)
                current_point = None
             
        if event == cv.EVENT_MOUSEMOVE:
            if current_point is not None: 
                mouse_pos = (x, y)
            else:
                mouse_pos = None

    while True:
        top_down = cv.imread("./assets/topdown.png")      
        top_down = cv.resize(top_down, (640, 640))     

        for zone in recs:
            p1 = zone.p1
            p2 = zone.p2
            color = zone.color
        
            top_down  = draw_center_text(top_down, p1, p2, zone.name, cv.FONT_HERSHEY_COMPLEX, 0.5, 1, zone.color)

        if current_point is not None and mouse_pos is not None:
            clr_seed = mouse_pos[0]
            cv.rectangle(top_down, current_point, mouse_pos, get_color(clr_seed), thickness=2)

        cv.imshow("Road Sections", top_down)
        cv.setMouseCallback("Road Sections", handle_point)

        if cv.waitKey(20) & 0xFF == ord('d'):
            break

    recs = [zone.to_dict() for zone in recs]

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    with open(outfile, "w") as file:
        json.dump(recs, file, indent=4)
else:
    print("Invalid mode value (try: gather, train, run, calibrate).")