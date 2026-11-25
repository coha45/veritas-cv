import zmq
import json
import math

from Enums import TrafficState, ZoneType, ViolationType
from Zone import Zone
from Leanbot import Leanbot


context = zmq.Context()

# ROUTER socket
socket = context.socket(zmq.ROUTER)
socket.bind("tcp://*:5555")

# PUB socket for FastAPI
state_pub = context.socket(zmq.PUB)
state_pub.bind("tcp://127.0.0.1:5556")


print("Veritas Broker Listening on Port 5555")


# ==========================================
# CANONICAL STATE
# ==========================================

# TOPDOWN owns canonical Leanbot state.
leanbot_data = {}

# Latest FOOT observations.
foot_observations = {
    "frame": None,
    "timestamp": None,
    "leanbots": {},
    "license_plates": {}
}

traffic_state = TrafficState.RED


# ==========================================
# VIOLATION PROCESSING
# ==========================================

def determine_violation(id, leanbot):

    leanbot = Leanbot.from_dict(leanbot)

    zone = leanbot.current_zone

    if zone is not None:

        if (
            zone.type == ZoneType.RESTRICTED
            and leanbot.time_since_entered > 0.2
        ):

            leanbot.add_violation(
                ViolationType.RESTRICTED_AREA.name
            )

        if (
            zone.zone_direction is not None
            and leanbot.angle is not None
        ):

            angle_in_deg = math.degrees(leanbot.angle)

            angle_diff = (
                (angle_in_deg - zone.zone_direction + 180) % 360
            ) - 180

            print("CURRENT ANGLE:", angle_in_deg)
            print("ZONE DIRECTION:", zone.zone_direction)
            print("ANGLE DIFFERENCE:", angle_diff)

            if abs(angle_diff) > 90:

                leanbot.add_violation(
                    ViolationType.WRONG_WAY.name
                )

    return leanbot.to_dict()


# ==========================================
# TOPDOWN HANDLER
# ==========================================

def handle_topdown(identity, payload):

    global leanbot_data

    incoming_data = json.loads(
        payload[0].decode("utf-8")
    )

    # Update canonical state
    leanbot_data = incoming_data

    # Prepare website state
    published_leanbots = []

    for key, leanbot in leanbot_data.items():

        nleanbot = determine_violation(
            key,
            leanbot
        )

        leanbot_data[key] = nleanbot

        published_leanbots.append({
            "id": key,
            "license_plate": nleanbot["license_plate"],
            "current_zone": nleanbot["current_zone"],
            "speed": nleanbot["speed"],
            "angle": nleanbot["angle"],
            "violations": nleanbot["violations"]
        })

    print("[BROKER] Publishing TOPDOWN State")

    state_pub.send_json({
        "type": "state_snapshot",
        "source": "TOPDOWN",
        "leanbots": published_leanbots,
        "traffic_state": traffic_state.name
    })

    # Return mutated canonical state
    response = json.dumps(
        leanbot_data
    ).encode("utf-8")

    socket.send_multipart([
        identity,
        response
    ])

    print("[BROKER] TOPDOWN Response Sent")


# ==========================================
# FOOT HANDLER
# ==========================================

def handle_foot(identity, payload):

    global foot_observations

    incoming_data = json.loads(
        payload[0].decode("utf-8")
    )

    # Validate source
    if incoming_data.get("camera_type") != "FOOT":
        socket.send_multipart([
            identity,
            json.dumps({
                "status": "error",
                "message": "Invalid camera type"
            }).encode("utf-8")
        ])
        return

    # Store latest FOOT observations.
    # These are camera-local IDs, NOT canonical IDs.
    foot_observations = {
        "frame": incoming_data.get("frame"),
        "timestamp": incoming_data.get("timestamp"),
        "leanbots": incoming_data.get("leanbots", {}),
        "license_plates": incoming_data.get(
            "license_plates",
            {}
        )
    }

    print(
        f"[BROKER] FOOT Frame: {foot_observations['frame']}"
    )

    print(
        f"[BROKER] FOOT Leanbots: "
        f"{len(foot_observations['leanbots'])}"
    )

    print(
        f"[BROKER] FOOT License Plates: "
        f"{len(foot_observations['license_plates'])}"
    )

    # Publish FOOT observations independently.
    state_pub.send_json({
        "type": "foot_snapshot",
        "source": "FOOT",
        "frame": foot_observations["frame"],
        "timestamp": foot_observations["timestamp"],
        "leanbots": foot_observations["leanbots"],
        "license_plates": foot_observations["license_plates"]
    })

    # Acknowledge receipt.
    socket.send_multipart([
        identity,
        json.dumps({
            "status": "received"
        }).encode("utf-8")
    ])


# ==========================================
# VIDEO HANDLERS
# ==========================================

def handle_video(identity, payload, camera_type):

    frame_bytes = payload[0]

    print(
        f"[BROKER] Publishing {camera_type} video frame"
    )

    state_pub.send_multipart([
        b"frame",
        camera_type.encode(),
        frame_bytes
    ])


# ==========================================
# MAIN EVENT LOOP
# ==========================================

while True:

    parts = socket.recv_multipart()

    identity = parts[0]
    payload = parts[1:]

    camera_identity = identity.decode("utf-8")

    if not payload:
        continue

    match camera_identity:

        case "TOPDOWN":
            handle_topdown(identity, payload)

        case "FOOT":
            handle_foot(identity, payload)

        case "VIDEO_TOPDOWN":
            handle_video(
                identity,
                payload,
                "TOPDOWN"
            )

        case "VIDEO_FOOT":
            handle_video(
                identity,
                payload,
                "FOOT"
            )

        case _:
            print(
                f"[BROKER] Unknown identity: {camera_identity}"
            )