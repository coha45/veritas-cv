import zmq
import json
from Enums import TrafficState
from Leanbot import Leanbot

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
                leanbots.append({
                    "id" : key,
                    "license_plate" : leanbot["license_plate"],
                    "current_zone" : leanbot["current_zone"],
                    "speed" : leanbot["speed"],
                    "angle" : leanbot["angle"]
                })

            print(leanbots)

            print("[BROKER] Publishing State")

            state_pub.send_json({
                "type": "state_snapshot",
                "source": "TOPDOWN",
                "leanbots": leanbots,
                "traffic_state": traffic_state.name
            })

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

    socket.send_multipart([
        identity,
        b"Hello, world"
    ])