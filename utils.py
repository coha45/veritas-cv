import cv2 as cv
import math
from random import seed, choice, randint
from os import path
from collections.abc import MutableMapping

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