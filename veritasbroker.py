import zmq
import cv2 as cv
from Leanbot import Leanbot 
from Enums import TrafficState
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
            leanbots = { key : Leanbot.from_dict(leanbot) for key, leanbot in payload.items() }
            print(leanbots)

        case "FOOT":
            break
        
    socket.send(b"HEllo, world")