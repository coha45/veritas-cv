import zmq
import json
from Enums import TrafficState, ZoneType, ViolationType
from Zone import Zone
from Leanbot import Leanbot
import math

context = zmq.Context()

# ROUTER socket
socket = context.socket(zmq.ROUTER)
socket.bind("tcp://*:5555")

# PUB socket for FastAPI
state_pub = context.socket(zmq.PUB)
state_pub.bind("tcp://127.0.0.1:5556")

print("Veritas Broker Listening on Port 5555")

leanbots = {}
leanbot_data = {}
traffic_state = TrafficState.RED

def determine_violation(id, leanbot):
    leanbot = Leanbot.from_dict(leanbot)
    zone = leanbot.current_zone

    if zone is not None:

        if zone.type == ZoneType.RESTRICTED and leanbot.time_since_entered > 0.2:
            leanbot.add_violation(ViolationType.RESTRICTED_AREA.name)

        if zone.zone_direction is not None and leanbot.angle is not None:

            angle_in_deg = math.degrees(leanbot.angle)

            angle_diff = (
                (angle_in_deg - zone.zone_direction + 180) % 360
            ) - 180

            print("CURRENT ANGLE:", angle_in_deg)
            print("ZONE DIRECTION:", zone.zone_direction)
            print("ANGLE DIFFERENCE:", angle_diff)

            if abs(angle_diff) > 90:
                leanbot.add_violation(ViolationType.WRONG_WAY.name)
    return leanbot.to_dict()

while True:
    parts = socket.recv_multipart()

    identity = parts[0]
    payload = parts[1:]

    match identity.decode():
        case "TOPDOWN":
            leanbot_data = json.loads(
                payload[0].decode("utf-8")
            )

            # Prepare Data to Match Website's Requirements
            leanbots = []
            for key, leanbot in leanbot_data.items(): 
                nleanbot = determine_violation(key, leanbot)
                leanbot_data[key] = nleanbot
                leanbots.append({
                    "id" : key,
                    "license_plate" : nleanbot["license_plate"],
                    "current_zone" : nleanbot["current_zone"],
                    "speed" : nleanbot["speed"],
                    "angle" : nleanbot["angle"],
                    "violations" : nleanbot["violations"]
                })

            print("[BROKER] Publishing State")

            state_pub.send_json({
                "type": "state_snapshot",
                "source": "TOPDOWN",
                "leanbots": leanbots,
                "traffic_state": traffic_state.name
            })
            response = json.dumps(leanbot_data).encode("utf-8")
            socket.send_multipart([
                identity,
                response
            ])
            print("[BROKER] Response Sent")

        case "FOOT":
            pass

        case "VIDEO_TOPDOWN":
            frame_bytes = payload[0]

            print("[BROKER] Publishing top-down video frame")

            state_pub.send_multipart([
                b"frame",
                b"TOPDOWN",
                frame_bytes
            ])

        case "VIDEO_FOOT":
            frame_bytes = payload[0]

            print("[BROKER] Publishing foot video frame")

            state_pub.send_multipart([
                b"frame",
                b"FOOT",
                frame_bytes
            ])