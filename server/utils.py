import cv2 as cv
import math
import platform
from random import seed, choice, randint
from os import path
from collections.abc import MutableMapping
import time
import json


def open_camera(source=0):
    """Open a USB/webcam source across Windows and Linux.

    Numeric strings are treated as device indexes. Linux device paths such as
    /dev/video0 are accepted; Linux sources are requested in YUYV format.
    """
    source_text = str(source).strip()
    device = int(source_text) if source_text.isdecimal() else source
    system = platform.system()
    if system == "Windows":
        backends = [cv.CAP_DSHOW, cv.CAP_MSMF, cv.CAP_ANY]
    elif system == "Linux":
        backends = [cv.CAP_V4L2, cv.CAP_ANY]
    else:
        backends = [cv.CAP_ANY]

    failures = []
    for backend in backends:
        capture = cv.VideoCapture(device, backend)
        if capture.isOpened():
            if system == "Linux":
                yuyv = cv.VideoWriter_fourcc(*"YUYV")
                format_set = capture.set(cv.CAP_PROP_FOURCC, yuyv)
                actual_fourcc = int(capture.get(cv.CAP_PROP_FOURCC))
                actual_format = "".join(
                    chr((actual_fourcc >> (8 * index)) & 0xFF)
                    for index in range(4)
                )
                print(
                    f"[CAMERA] Requested YUYV on {source_text}; "
                    f"accepted={format_set}, reported={actual_format or 'unknown'}",
                    flush=True,
                )
            capture.set(cv.CAP_PROP_BUFFERSIZE, 1)
            backend_name = capture.getBackendName() if hasattr(capture, "getBackendName") else str(backend)
            print(f"[CAMERA] Opened source {source_text} with {backend_name}", flush=True)
            return capture
        capture.release()
        failures.append(str(backend))

    source_hint = "USB camera index or video path"
    raise RuntimeError(
        f"Could not open camera source {source_text!r} on {system}. "
        f"Tried OpenCV backends {', '.join(failures)}; check the {source_hint}, "
        "permissions, and whether another app is using the camera."
    )

def gen_key():
    ch = "abcdefghijklmnopqrstuvwxyz1234567890"
    return "".join([choice(ch) for i in range(randint(10,20))])

def get_color(cls_num):
    seed(cls_num)
    return tuple(randint(0,255) for _ in range(3))

def save_img(outdir, cap, drawn, frame):
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
    x2 = int(x1 + length*math.cos(angle))
    y2 = int(y1 + length*math.sin(angle))

    cv.arrowedLine(frame, (x1, y1), (x2, y2), color, thickness)

    return frame

def get_angle_in_degrees(p1, p2):
    return math.degrees(get_angle_in_radians(p1, p2))

def draw_center_text(frame, p1, p2, text, font, scale, thickness, color):
    x1, y1 = p1
    x2, y2 = p2
    cv.rectangle(frame, p1, p2, color, thickness=2)

    (text_width, text_height), baseline = cv.getTextSize(text, font, scale, thickness)
    x = x1 + (((x2 - x1) - text_width) // 2)
    y = y1 + (((y2 - y1) + text_height) // 2)
    centroid = (x, y)

    cv.putText(frame, text, centroid, font, scale, color, 1)

    return frame

def publish_frame(publisher, frame, identity, camera_id):
    success, encoded = cv.imencode(
        ".jpg",
        frame,
        [
            cv.IMWRITE_JPEG_QUALITY,75
        ]
    )

    if not success:
        return

    metadata = {
        "type" : "frame",
        "camera_id" : "camera_id",
        "timestamp" : time.time()
    }

    publisher.send(encoded.tobytes())

