
import atexit
import zmq
import json
import math
import uuid

from pathlib import Path

from Enums import TrafficState, ZoneType, ViolationType
from Leanbot import Leanbot
from traffic_output import TrafficOutput


# ==========================================
# CONFIGURATION
# ==========================================

MAX_MATCH_DISTANCE = 80.0
MIN_PLATE_OVERLAP = 0.50

# This directory is also mounted by FastAPI.
CAPTURE_DIR = Path(__file__).resolve().parent / "captures"
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

CAPTURE_URL_PREFIX = "/captures"

TRAFFIC_CONFIG_PATH = Path(__file__).resolve().parent / "traffic_checkers.json"
try:
    with TRAFFIC_CONFIG_PATH.open("r", encoding="utf-8") as traffic_config_file:
        traffic_config = json.load(traffic_config_file) if TRAFFIC_CONFIG_PATH.stat().st_size else {}
except json.JSONDecodeError:
    traffic_config = {}

TRAFFIC_CHECKERS = traffic_config.get("checkers", [])
INTERSECTION_ZONE = traffic_config.get("intersection_zone", "main_intersection")
TRAFFIC_CHECKERS_BY_ID = {checker["id"]: checker for checker in TRAFFIC_CHECKERS}
ZONE_TO_TRAFFIC_CHECKER = {
    zone_name: checker["id"]
    for checker in TRAFFIC_CHECKERS
    if checker.get("type", "road") == "road"
    for zone_name in checker["approach_zones"]
}

road_checkers = [checker for checker in TRAFFIC_CHECKERS if checker.get("type", "road") == "road"]
pedestrian_checkers = [checker for checker in TRAFFIC_CHECKERS if checker.get("type") == "pedestrian"]
if TRAFFIC_CHECKERS and (
    len(TRAFFIC_CHECKERS_BY_ID) != 2 + len(pedestrian_checkers)
    or len(road_checkers) != 2
    or len(pedestrian_checkers) > 1
    or any(not checker["approach_zones"] for checker in road_checkers)
    or any(not checker["approach_zones"] for checker in pedestrian_checkers)
):
    raise ValueError("When configured, traffic_checkers.json must define two road checkers and optionally one pedestrian checker, each with at least one zone")


# ==========================================
# ZMQ
# ==========================================

context = zmq.Context()

socket = context.socket(zmq.ROUTER)
socket.bind("tcp://*:5555")

state_pub = context.socket(zmq.PUB)
state_pub.bind("tcp://127.0.0.1:5556")

# Local-only control channel used by the FastAPI bridge.
control_socket = context.socket(zmq.REP)
control_socket.bind("tcp://127.0.0.1:5557")

print("[BROKER] Veritas Broker Listening on Port 5555")
print("[BROKER] Traffic control listening on 127.0.0.1:5557")
print(f"[BROKER] Capture directory: {CAPTURE_DIR}")


# ==========================================
# CANONICAL STATE
# ==========================================

leanbot_data = {}
topdown_positions = {}
topdown_bboxes = {}
previous_topdown_bboxes = {}

foot_observations = {
    "frame": None,
    "timestamp": None,
    "leanbots": {},
    "license_plates": {}
}

# Canonical ID -> evidence record
license_plate_captures = {}

traffic_output = TrafficOutput(TRAFFIC_CHECKERS)
traffic_states = {
    checker_id: traffic_output.set_state(checker_id, TrafficState.RED)
    for checker_id in TRAFFIC_CHECKERS_BY_ID
}
previous_zone_observations = {}
topdown_snapshot_index = 0
atexit.register(traffic_output.close)


def publish_traffic_states():
    state_pub.send_json({
        "type": "traffic_state",
        "traffic_states": {
            checker_id: state.name
            for checker_id, state in traffic_states.items()
        },
        "traffic_checkers": TRAFFIC_CHECKERS,
        "intersection_zone": INTERSECTION_ZONE,
    })


def set_traffic_state(checker_id, state_name):

    if checker_id not in TRAFFIC_CHECKERS_BY_ID:
        raise ValueError(f"Unknown traffic checker: {checker_id}")

    next_state = TrafficState[str(state_name).strip().upper()]
    traffic_output.set_state(checker_id, next_state)
    traffic_states[checker_id] = next_state
    publish_traffic_states()

    print(f"[TRAFFIC] {checker_id} changed to {next_state.name}")
    return {
        "ok": True,
        "checker_id": checker_id,
        "traffic_state": next_state.name,
    }


# ==========================================
# GEOMETRY
# ==========================================

def plate_overlaps_leanbot(
    leanbot_bbox,
    plate_bbox,
    min_overlap=MIN_PLATE_OVERLAP
):

    lx1, ly1, lx2, ly2 = leanbot_bbox
    px1, py1, px2, py2 = plate_bbox

    ix1 = max(lx1, px1)
    iy1 = max(ly1, py1)
    ix2 = min(lx2, px2)
    iy2 = min(ly2, py2)

    intersection = (
        max(0, ix2 - ix1) *
        max(0, iy2 - iy1)
    )

    plate_area = (
        max(0, px2 - px1) *
        max(0, py2 - py1)
    )

    if plate_area <= 0:
        return False

    overlap = intersection / plate_area

    return overlap >= min_overlap


# ==========================================
# FOOT / TOPDOWN ASSOCIATION
# ==========================================

def associate_foot_leanbots():

    candidates = []

    for foot_id, observation in foot_observations["leanbots"].items():

        coordinates = observation.get("coordinates")

        if not coordinates or len(coordinates) != 2:
            continue

        fx, fy = coordinates

        for topdown_id, position in topdown_positions.items():

            if not position or len(position) != 2:
                continue

            tx, ty = position

            distance = math.hypot(
                fx - tx,
                fy - ty
            )

            if distance <= MAX_MATCH_DISTANCE:

                candidates.append((
                    distance,
                    str(topdown_id),
                    str(foot_id),
                    observation
                ))

    candidates.sort(key=lambda item: item[0])

    matched_topdown = set()
    matched_foot = set()

    matches = {}

    for distance, topdown_id, foot_id, observation in candidates:

        if topdown_id in matched_topdown:
            continue

        if foot_id in matched_foot:
            continue

        matched_topdown.add(topdown_id)
        matched_foot.add(foot_id)

        matches[topdown_id] = {
            "foot_track_id": foot_id,
            "coordinates": observation["coordinates"],
            "distance": round(distance, 2),
            "confidence": observation.get("confidence", 0)
        }

    print("\n[ASSOCIATION]")
    print(f"TOPDOWN: {len(topdown_positions)}")
    print(f"FOOT: {len(foot_observations['leanbots'])}")
    print(f"MATCHED: {len(matches)}")

    for topdown_id, match in matches.items():

        print(
            f"  TOPDOWN {topdown_id} "
            f"<-> FOOT {match['foot_track_id']} "
            f"| Distance: {match['distance']:.2f}px"
        )

    return matches


# ==========================================
# SAVE PLATE EVIDENCE
# ==========================================

def save_plate_evidence(
    topdown_id,
    plate_id,
    plate,
    image_bytes
):

    """
    Saves one confirmed plate crop per canonical Leanbot.

    Returns the evidence metadata.
    """

    safe_id = "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in str(topdown_id)
    )

    filename = (
        f"leanbot_{safe_id}_plate_{uuid.uuid4().hex[:8]}.jpg"
    )

    filepath = CAPTURE_DIR / filename

    try:

        if not image_bytes:
            print("[CAPTURE] Empty image data")
            return None

        # Write actual JPEG crop received from FOOT.
        filepath.write_bytes(image_bytes)

        capture = {
            "image_url": f"{CAPTURE_URL_PREFIX}/{filename}",
            "filename": filename,
            "timestamp": foot_observations["timestamp"],
            "frame": foot_observations["frame"],
            "camera": "FOOT",
            "plate_track_id": str(plate_id),
            "bbox": plate["bbox"],
            "confidence": plate.get("confidence", 0)
        }

        print("\n" + "=" * 55)
        print("[PLATE EVIDENCE SAVED]")
        print(f"Canonical Leanbot: {topdown_id}")
        print(f"Plate Track ID: {plate_id}")
        print(f"File: {filepath}")
        print(f"URL: {capture['image_url']}")
        print("=" * 55)

        return capture

    except OSError as error:

        print(f"[CAPTURE ERROR] {error}")
        return None


# ==========================================
# PLATE ASSOCIATION AND CAPTURE
# ==========================================

def process_plate_captures(matches, image_frames):

    captured_this_frame = []

    plates = foot_observations["license_plates"]
    foot_leanbots = foot_observations["leanbots"]

    for topdown_id, match in matches.items():

        # Already have evidence for this canonical Leanbot.
        if topdown_id in license_plate_captures:
            continue

        foot_id = str(match["foot_track_id"])

        foot_observation = foot_leanbots.get(foot_id)

        if foot_observation is None:
            continue

        leanbot_bbox = foot_observation.get("bbox")

        if leanbot_bbox is None:
            continue

        for plate_id, plate in plates.items():

            plate_bbox = plate.get("bbox")

            if plate_bbox is None:
                continue

            overlaps = plate_overlaps_leanbot(
                leanbot_bbox,
                plate_bbox
            )

            print(
                f"[PLATE CHECK] Leanbot {topdown_id} "
                f"| Plate {plate_id} "
                f"| Overlap: {overlaps}"
            )

            if not overlaps:
                continue

            image_index = plate.get("image_index")

            if image_index is None:
                continue

            if not 0 <= image_index < len(image_frames):
                print("[CAPTURE ERROR] Invalid image index")
                continue

            image_bytes = image_frames[image_index]

            capture = save_plate_evidence(
                topdown_id,
                plate_id,
                plate,
                image_bytes
            )

            if capture is None:
                continue

            # Associate evidence with canonical Leanbot.
            license_plate_captures[topdown_id] = capture

            # Update canonical state immediately.
            if topdown_id in leanbot_data:

                leanbot_data[topdown_id]["license_plate"] = True

            captured_this_frame.append(str(plate_id))

            print(
                f"[SUCCESS] Leanbot {topdown_id} "
                "LICENSE_PLATE = TRUE"
            )

            # One plate capture per Leanbot.
            break

    return captured_this_frame


# ==========================================
# VIOLATION PROCESSING
# ==========================================

def determine_violation(leanbot):

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

            if abs(angle_diff) > 90:

                leanbot.add_violation(
                    ViolationType.WRONG_WAY.name
                )

    return leanbot.to_dict()


def detect_red_light_running(leanbot_id, leanbot_data_item):
    """Flag entry into the intersection from a red-controlled road."""
    leanbot_id = str(leanbot_id)
    zone = leanbot_data_item.get("current_zone") or {}
    current_zone_name = zone.get("name") if isinstance(zone, dict) else None
    previous = previous_zone_observations.get(leanbot_id)
    triggered_checker = None

    if current_zone_name == INTERSECTION_ZONE and previous is not None:
        checker_id = ZONE_TO_TRAFFIC_CHECKER.get(previous["zone"])
        observation_is_recent = topdown_snapshot_index - previous["snapshot"] <= 2
        if (
            observation_is_recent
            and checker_id
            and traffic_states[checker_id] == TrafficState.RED
        ):
            triggered_checker = checker_id

    if current_zone_name:
        previous_zone_observations[leanbot_id] = {
            "zone": current_zone_name,
            "snapshot": topdown_snapshot_index,
        }
    elif previous is not None and topdown_snapshot_index - previous["snapshot"] > 2:
        previous_zone_observations.pop(leanbot_id, None)

    if triggered_checker:
        leanbot = Leanbot.from_dict(leanbot_data_item)
        leanbot.add_violation(ViolationType.RUNNING_RED_LIGHT.name)
        print(
            f"[VIOLATION] Leanbot {leanbot_id} entered {INTERSECTION_ZONE} "
            f"from {triggered_checker} while RED"
        )
        return leanbot.to_dict()

    return leanbot_data_item


def detect_vehicle_collisions(leanbot_data, bboxes):
    """Flag a moving Leanbot whose bounding box collides with another track."""
    global previous_topdown_bboxes
    ids = [str(track_id) for track_id in bboxes if str(track_id) in leanbot_data]
    current_boxes = {track_id: bboxes[track_id] for track_id in ids}

    def center(box):
        return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

    def overlap_ratio(first, second):
        ix1, iy1 = max(first[0], second[0]), max(first[1], second[1])
        ix2, iy2 = min(first[2], second[2]), min(first[3], second[3])
        intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        area_a = max(0, first[2] - first[0]) * max(0, first[3] - first[1])
        area_b = max(0, second[2] - second[0]) * max(0, second[3] - second[1])
        union = area_a + area_b - intersection
        return intersection / union if union > 0 else 0

    for index, first_id in enumerate(ids):
        for second_id in ids[index + 1:]:
            first_box, second_box = current_boxes[first_id], current_boxes[second_id]
            previous_first = previous_topdown_bboxes.get(first_id)
            previous_second = previous_topdown_bboxes.get(second_id)
            if not previous_first or not previous_second or overlap_ratio(first_box, second_box) < 0.1:
                continue

            first_now, second_now = center(first_box), center(second_box)
            first_before, second_before = center(previous_first), center(previous_second)
            distance_now = math.dist(first_now, second_now)
            distance_before = math.dist(first_before, second_before)
            if distance_now >= distance_before:
                continue

            moving_into = []
            for track_id, now, before, other in (
                (first_id, first_now, first_before, second_now),
                (second_id, second_now, second_before, first_now),
            ):
                speed = float(leanbot_data[track_id].get("speed") or 0)
                movement = (now[0] - before[0], now[1] - before[1])
                toward_other = (other[0] - now[0], other[1] - now[1])
                if speed >= 8 and movement[0] * toward_other[0] + movement[1] * toward_other[1] > 0:
                    moving_into.append(track_id)

            for track_id in moving_into:
                leanbot = Leanbot.from_dict(leanbot_data[track_id])
                leanbot.add_violation(ViolationType.VEHICLE_COLLISION.name)
                leanbot_data[track_id] = leanbot.to_dict()
                print(f"[VIOLATION] Leanbot {track_id} collided with another tracked Leanbot")

    previous_topdown_bboxes = current_boxes
    return leanbot_data


# ==========================================
# TOPDOWN HANDLER
# ==========================================

def handle_topdown(identity, payload):

    global leanbot_data
    global topdown_positions
    global topdown_bboxes
    global topdown_snapshot_index

    topdown_snapshot_index += 1

    incoming_data = json.loads(
        payload[0].decode("utf-8")
    )

    if (
        "leanbots" in incoming_data
        and "positions" in incoming_data
    ):

        leanbot_data = incoming_data["leanbots"]

        topdown_positions = {
            str(key): value
            for key, value in incoming_data["positions"].items()
        }
        topdown_bboxes = {
            str(key): value for key, value in incoming_data.get("bboxes", {}).items()
        }

    else:

        print("[WARNING] Legacy TOPDOWN payload received")

        leanbot_data = incoming_data
        topdown_bboxes = {}

    leanbot_data = detect_vehicle_collisions(leanbot_data, topdown_bboxes)
    published_leanbots = []

    for key, leanbot in leanbot_data.items():

        leanbot = detect_red_light_running(key, leanbot)
        updated = determine_violation(leanbot)

        # Preserve confirmed plate state.
        if key in license_plate_captures:

            updated["license_plate"] = True

        leanbot_data[key] = updated

        published_leanbots.append({

            "id": key,

            "license_plate": updated.get(
                "license_plate", False
            ),

            "license_plate_capture": (
                license_plate_captures.get(key)
            ),

            "current_zone": updated.get("current_zone"),
            "speed": updated.get("speed"),
            "angle": updated.get("angle"),
            "violations": updated.get("violations", [])
        })

    print(
        f"\n[BROKER] TOPDOWN: {len(leanbot_data)} Leanbots"
    )

    state_pub.send_json({
        "type": "state_snapshot",
        "source": "TOPDOWN",
        "leanbots": published_leanbots,
        "traffic_states": {
            checker_id: state.name
            for checker_id, state in traffic_states.items()
        },
        "traffic_checkers": TRAFFIC_CHECKERS,
        "intersection_zone": INTERSECTION_ZONE,
    })

    # Return canonical state to TOPDOWN.
    socket.send_multipart([
        identity,
        json.dumps({
            "leanbots": leanbot_data,
            "traffic_states": {
                checker_id: state.name
                for checker_id, state in traffic_states.items()
            },
        }).encode("utf-8")
    ])


# ==========================================
# FOOT HANDLER
# ==========================================

def handle_foot(identity, payload):

    global foot_observations

    # First frame is JSON.
    incoming_data = json.loads(
        payload[0].decode("utf-8")
    )

    # Remaining frames are JPEG crops.
    image_frames = payload[1:]

    if incoming_data.get("camera_type") != "FOOT":

        socket.send_multipart([
            identity,
            json.dumps({
                "status": "error",
                "message": "Invalid camera type"
            }).encode("utf-8")
        ])

        return

    foot_observations = {
        "frame": incoming_data.get("frame"),
        "timestamp": incoming_data.get("timestamp"),
        "leanbots": incoming_data.get("leanbots", {}),
        "license_plates": incoming_data.get(
            "license_plates", {}
        )
    }

    print("\n" + "=" * 55)
    print("[FOOT RECEIVED]")
    print(f"Frame: {foot_observations['frame']}")
    print(f"Leanbots: {len(foot_observations['leanbots'])}")
    print(f"Plates: {len(foot_observations['license_plates'])}")
    print(f"JPEG crops: {len(image_frames)}")

    # Associate FOOT with canonical TOPDOWN IDs.
    matches = associate_foot_leanbots()

    # Check overlap and save evidence.
    captured_plate_ids = process_plate_captures(
        matches,
        image_frames
    )

    # Publish FOOT observations.
    state_pub.send_json({
        "type": "foot_snapshot",
        "source": "FOOT",
        "frame": foot_observations["frame"],
        "timestamp": foot_observations["timestamp"],
        "leanbots": foot_observations["leanbots"],
        "license_plates": foot_observations["license_plates"],
        "matches": matches,
        "captured_plate_ids": captured_plate_ids
    })

    print(
        f"[FOOT] New evidence captures: "
        f"{len(captured_plate_ids)}"
    )

    # Acknowledge camera.
    socket.send_multipart([
        identity,
        json.dumps({
            "status": "received",
            "matched": len(matches),
            "captured": len(captured_plate_ids)
        }).encode("utf-8")
    ])


# ==========================================
# VIDEO HANDLER
# ==========================================

def handle_video(identity, payload, camera_type):

    state_pub.send_multipart([
        b"frame",
        camera_type.encode(),
        payload[0]
    ])


# ==========================================
# MAIN EVENT LOOP
# ==========================================

poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)
poller.register(control_socket, zmq.POLLIN)

while True:

    ready = dict(poller.poll())

    if control_socket in ready:
        try:
            command = control_socket.recv_json()

            if not isinstance(command, dict) or command.get("command") != "set_traffic_state":
                raise ValueError("Expected command=set_traffic_state")

            response = set_traffic_state(
                command.get("checker_id", ""),
                command.get("state", ""),
            )

        except Exception as error:
            response = {"ok": False, "error": str(error)}

        control_socket.send_json(response)

    if socket not in ready:
        continue

    parts = socket.recv_multipart()

    if len(parts) < 2:
        continue

    identity = parts[0]
    payload = parts[1:]

    camera_identity = identity.decode("utf-8")

    if camera_identity == "TOPDOWN":

        handle_topdown(identity, payload)

    elif camera_identity == "FOOT":

        handle_foot(identity, payload)

    elif camera_identity == "VIDEO_TOPDOWN":

        handle_video(identity, payload, "TOPDOWN")

    elif camera_identity == "VIDEO_FOOT":

        handle_video(identity, payload, "FOOT")

    else:

        print(
            f"[BROKER] Unknown identity: {camera_identity}"
        )
