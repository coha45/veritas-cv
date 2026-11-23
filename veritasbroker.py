import zmq
import cv2 as cv
from veritascli import Leanbot, TrafficState, get_dist
import json

context = zmq.Context()

socket = context.socket(zmq.ROUTER)

socket.bind("tcp://*:5555")

print("Veritas Broker Listening on Port 5555")

leanbots = None
traffic_state = TrafficState.RED

while True:
    identity, payload = socket.recv_multipart()

    match identity.decode():
        case "TOPDOWN":
            payload = json.loads(payload.decode("utf-8"))
            print(payload)

        case "FOOT":
            break
        
    socket.send(b"HEllo, world")