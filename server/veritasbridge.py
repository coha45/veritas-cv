
import asyncio
import ipaddress
import threading
import zmq
import json
import numpy as np
from fractions import Fraction
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import av
import cv2 as cv
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from database import append_approved_violations, get_plate_image, initialize, list_records, save_approved, update_plate
import portal_database as portal_db


# ==========================================
# ZERO MQ CONFIGURATION
# ==========================================

context = zmq.Context()

print("[BRIDGE] Veritas Broker PUB :5556 configured")


# ==========================================
# GLOBAL STATE
# ==========================================

clients = set()

main_loop = None

shutdown_event = threading.Event()

broadcast_lock = None
latest_camera_frames = {"TOPDOWN": None, "FOOT": None}
camera_frame_events = {}
peer_connections = set()
live_violation_signatures = {}


class CameraVideoTrack(VideoStreamTrack):
    """Serve fresh frames only, preventing encoder backlog when inference is slow."""
    def __init__(self, camera_id):
        super().__init__()
        self.camera_id = camera_id
        self.frame_number = 0
        self.started_at = None

    async def recv(self):
        event = camera_frame_events[self.camera_id]
        await event.wait()
        event.clear()
        image = latest_camera_frames.get(self.camera_id)
        if image is None:
            return await self.recv()
        now = asyncio.get_running_loop().time()
        if self.started_at is None:
            self.started_at = now
        self.frame_number += 1
        frame = av.VideoFrame.from_ndarray(image, format="bgr24")
        frame.pts = int((now - self.started_at) * 90000)
        frame.time_base = Fraction(1, 90000)
        return frame


# ==========================================
# WEBSOCKET BROADCAST - JSON
# ==========================================

async def broadcast(message):

    async with broadcast_lock:

        disconnected = []

        for client in list(clients):

            try:
                await client.send_json(message)

            except Exception as e:
                print("[WS] Send error:", repr(e))
                disconnected.append(client)

        for client in disconnected:
            clients.discard(client)


# ==========================================
# WEBSOCKET BROADCAST - VIDEO
# ==========================================

async def broadcast_frame(camera_id, frame_bytes):
    print(
        f"[VIDEO] Camera: {camera_id} | "
        f"Frame size: {len(frame_bytes)} bytes | "
        f"JPEG header: {frame_bytes[:4].hex()}"
    )
    async with broadcast_lock:

        disconnected = []

        for client in list(clients):

            try:

                # Send frame metadata
                await client.send_json({
                    "type": "frame",
                    "camera_id": camera_id
                })

                # Send JPEG binary
                await client.send_bytes(frame_bytes)

            except Exception as e:

                print("[WS] Frame error:", repr(e))
                disconnected.append(client)

        for client in disconnected:
            clients.discard(client)


# ==========================================
# ZMQ BACKGROUND THREAD
# ==========================================

def zmq_listener(loop):

    print("[ZMQ] Background listener started")

    subscriber = context.socket(zmq.SUB)

    subscriber.connect("tcp://127.0.0.1:5556")

    # Subscribe to all messages
    subscriber.setsockopt(zmq.SUBSCRIBE, b"")

    try:

        while not shutdown_event.is_set():

            if not subscriber.poll(500):
                continue

            parts = subscriber.recv_multipart()

            # ==================================
            # EXISTING JSON STATE MESSAGE
            # ==================================

            if len(parts) == 1:

                message = json.loads(parts[0])
                if message.get("type") == "state_snapshot":
                    live_leanbots = message.get("leanbots", [])
                    changed_leanbots = []
                    active_ids = set()
                    if isinstance(live_leanbots, list):
                        for bot in live_leanbots:
                            if not isinstance(bot, dict) or bot.get("id") is None:
                                continue
                            leanbot_id = str(bot["id"])
                            active_ids.add(leanbot_id)
                            signature = json.dumps(bot.get("violations") or [], sort_keys=True)
                            if live_violation_signatures.get(leanbot_id) != signature:
                                live_violation_signatures[leanbot_id] = signature
                                changed_leanbots.append(bot)
                    for stale_id in set(live_violation_signatures) - active_ids:
                        del live_violation_signatures[stale_id]
                    if changed_leanbots:
                        try:
                            append_approved_violations(changed_leanbots)
                        except Exception as error:
                            print("[DATABASE] Could not append live violations:", repr(error))
                future = asyncio.run_coroutine_threadsafe(
                    broadcast(message),
                    loop
                )

            # ==================================
            # VIDEO FRAME MESSAGE
            # ==================================

            elif len(parts) == 3:

                topic, camera_id, frame_bytes = parts

                if topic != b"frame":
                    continue

                camera_name = camera_id.decode("utf-8")
                if camera_name in latest_camera_frames:
                    decoded = cv.imdecode(
                        np.frombuffer(frame_bytes, dtype=np.uint8), cv.IMREAD_COLOR
                    )
                    if decoded is not None:
                        latest_camera_frames[camera_name] = decoded
                        event = camera_frame_events.get(camera_name)
                        if event is not None:
                            loop.call_soon_threadsafe(event.set)
                continue

            else:

                print("[ZMQ] Unknown message format:", len(parts))
                continue

            # Report asynchronous errors
            def report_result(f):
                try:
                    f.result()
                except Exception as e:
                    print("[WS] Broadcast task error:", repr(e))

            future.add_done_callback(report_result)

    except zmq.ZMQError as e:

        if not shutdown_event.is_set():
            print("[ZMQ] Error:", repr(e))

    finally:

        subscriber.close(linger=0)

        print("[ZMQ] Listener stopped")


# ==========================================
# FASTAPI LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global main_loop, broadcast_lock

    print("[BRIDGE] Starting Veritas WebSocket Bridge")

    main_loop = asyncio.get_running_loop()

    broadcast_lock = asyncio.Lock()
    initialize()
    portal_db.initialize()
    camera_frame_events.clear()
    camera_frame_events.update({camera_id: asyncio.Event() for camera_id in latest_camera_frames})

    shutdown_event.clear()

    listener_thread = threading.Thread(
        target=zmq_listener,
        args=(main_loop,),
        daemon=True
    )

    listener_thread.start()

    yield

    print("[BRIDGE] Shutting down")

    shutdown_event.set()

    await asyncio.gather(*(pc.close() for pc in list(peer_connections)), return_exceptions=True)
    peer_connections.clear()

    listener_thread.join(timeout=2)

    context.term()

    print("[BRIDGE] Shutdown complete")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}):[0-9]+$",
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Serve plate evidence saved by veritasbroker.py at the same URL prefix
# included in its published capture metadata.
CAPTURE_DIR = Path(__file__).resolve().parent / "captures"
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/captures",
    StaticFiles(directory=CAPTURE_DIR),
    name="captures",
)

@app.get("/api/database/leanbots")
async def get_leanbot_records():
    return {"records": list_records()}


def _portal_identity(request: Request, admin=False):
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    user = portal_db.authenticate(token if scheme.lower() == "bearer" else "")
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    if admin and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Portal administrator access is required")
    return token, user


async def _portal_json(request: Request):
    try:
        body = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail="Expected a JSON request") from error
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Expected a JSON object")
    return body


@app.post("/api/portal/auth/signup")
async def portal_signup(request: Request):
    body = await _portal_json(request)
    try:
        token, user = await asyncio.to_thread(
            portal_db.signup, body.get("email"), body.get("password"),
            body.get("first_name"), body.get("last_name"), body.get("phone", ""),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"token": token, "user": user}


@app.post("/api/portal/auth/login")
async def portal_login(request: Request):
    body = await _portal_json(request)
    try:
        token, user = await asyncio.to_thread(portal_db.login, body.get("email"), body.get("password"))
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    return {"token": token, "user": user}


@app.post("/api/portal/auth/logout")
async def portal_logout(request: Request):
    token, _ = _portal_identity(request)
    await asyncio.to_thread(portal_db.logout, token)
    return {"ok": True}


@app.get("/api/portal/me")
async def portal_me(request: Request):
    _, user = _portal_identity(request)
    return {"user": user}


@app.patch("/api/portal/me/profile")
async def portal_update_profile(request: Request):
    _, user = _portal_identity(request)
    body = await _portal_json(request)
    try:
        updated = await asyncio.to_thread(
            portal_db.update_profile, user["id"], body.get("first_name"),
            body.get("last_name"), body.get("phone", ""),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"user": updated}


@app.post("/api/portal/me/password")
async def portal_change_password(request: Request):
    _, user = _portal_identity(request)
    body = await _portal_json(request)
    try:
        token = await asyncio.to_thread(
            portal_db.change_password, user["id"], body.get("current_password"), body.get("new_password"),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"token": token}


@app.get("/api/portal/me/vehicles")
async def portal_vehicles(request: Request):
    _, user = _portal_identity(request)
    vehicles = await asyncio.to_thread(portal_db.list_vehicles, user["id"])
    return {"vehicles": vehicles}


@app.post("/api/portal/me/vehicles")
async def portal_add_vehicle(request: Request):
    _, user = _portal_identity(request)
    body = await _portal_json(request)
    try:
        vehicle = await asyncio.to_thread(portal_db.add_vehicle, user["id"], body)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"vehicle": vehicle}


@app.delete("/api/portal/me/vehicles/{vehicle_id}")
async def portal_remove_vehicle(vehicle_id: str, request: Request):
    _, user = _portal_identity(request)
    removed = await asyncio.to_thread(portal_db.remove_vehicle, user["id"], vehicle_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Vehicle record not found")
    return {"ok": True}


@app.get("/api/portal/me/violations")
async def portal_violations(request: Request):
    _, user = _portal_identity(request)
    violations = await asyncio.to_thread(portal_db.user_violations, user["id"])
    return {"violations": violations}


@app.post("/api/portal/me/disputes")
async def portal_create_dispute(request: Request):
    _, user = _portal_identity(request)
    body = await _portal_json(request)
    try:
        dispute = await asyncio.to_thread(
            portal_db.create_dispute, user["id"], body.get("leanbot_id"),
            body.get("violation_type"), body.get("reason"),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"dispute": dispute}


@app.get("/api/portal/me/payments")
async def portal_payments(request: Request):
    _portal_identity(request)
    return {"payments": []}


@app.get("/api/portal/admin/vehicles")
async def portal_admin_vehicles(request: Request, status: str = "pending"):
    _portal_identity(request, admin=True)
    vehicles = await asyncio.to_thread(portal_db.admin_vehicles, status)
    return {"vehicles": vehicles}


@app.post("/api/portal/admin/vehicles/{vehicle_id}/decision")
async def portal_admin_vehicle_decision(vehicle_id: str, request: Request):
    _, user = _portal_identity(request, admin=True)
    body = await _portal_json(request)
    try:
        vehicle = await asyncio.to_thread(
            portal_db.decide_vehicle, user["id"], vehicle_id, body.get("decision"), body.get("remarks", ""),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle application not found")
    return {"vehicle": vehicle}


@app.get("/api/portal/admin/unassigned-violations")
async def portal_admin_unassigned_violations(request: Request):
    _portal_identity(request, admin=True)
    violations = await asyncio.to_thread(portal_db.unassigned_violations)
    return {"violations": violations}


@app.get("/api/portal/admin/disputes")
async def portal_admin_disputes(request: Request):
    _portal_identity(request, admin=True)
    disputes = await asyncio.to_thread(portal_db.admin_disputes)
    return {"disputes": disputes}


@app.patch("/api/portal/admin/disputes/{dispute_id}")
async def portal_admin_decide_dispute(dispute_id: str, request: Request):
    _, user = _portal_identity(request, admin=True)
    body = await _portal_json(request)
    try:
        dispute = await asyncio.to_thread(
            portal_db.decide_dispute, user["id"], dispute_id,
            body.get("status"), body.get("staff_note", ""),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if dispute is None:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return {"dispute": dispute}


@app.get("/api/portal/admin/fines")
async def portal_admin_fines(request: Request):
    _portal_identity(request, admin=True)
    return {"fines": await asyncio.to_thread(portal_db.list_fines)}


@app.put("/api/portal/admin/fines")
async def portal_admin_set_fine(request: Request):
    _portal_identity(request, admin=True)
    body = await _portal_json(request)
    try:
        fine = await asyncio.to_thread(
            portal_db.set_fine, body.get("violation_type"), body.get("amount"), body.get("currency", "PHP"),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"fine": fine}


@app.get("/api/portal/admin/payments")
async def portal_admin_payments(request: Request):
    _portal_identity(request, admin=True)
    return {"payments": []}


@app.get("/api/database/leanbots/{leanbot_id}/plate-image")
async def get_leanbot_plate_image(leanbot_id: str):
    image = get_plate_image(leanbot_id)
    if image is None:
        raise HTTPException(status_code=404, detail="No plate image is stored for this Leanbot")
    image_bytes, media_type = image
    return Response(
        content=image_bytes,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.patch("/api/database/leanbots/{leanbot_id}/plate")
async def edit_leanbot_plate(leanbot_id: str, request: Request):
    try:
        body = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail="Expected JSON with license_plate") from error
    plate = body.get("license_plate") if isinstance(body, dict) else None
    if not isinstance(plate, str):
        raise HTTPException(status_code=400, detail="license_plate must be text")
    plate = plate.strip()
    if len(plate) > 32:
        raise HTTPException(status_code=400, detail="Plate text must be 32 characters or fewer")
    saved_plate = plate or None
    updated = await asyncio.to_thread(update_plate, leanbot_id, saved_plate)
    if not updated:
        raise HTTPException(status_code=404, detail="Approved Leanbot record not found")
    return {"ok": True, "leanbot_id": leanbot_id, "license_plate": saved_plate}


@app.post("/api/webrtc/offer")
async def webrtc_offer(request: Request):
    try:
        body = await request.json()
        camera_id = body.get("camera_id")
        if camera_id not in latest_camera_frames or not body.get("sdp") or not body.get("type"):
            raise ValueError("camera_id, sdp, and type are required")
        pc = RTCPeerConnection()
        peer_connections.add(pc)

        @pc.on("connectionstatechange")
        async def on_connection_state_change():
            if pc.connectionState in {"failed", "closed"}:
                peer_connections.discard(pc)
            if pc.connectionState == "failed":
                await pc.close()

        await pc.setRemoteDescription(RTCSessionDescription(sdp=body["sdp"], type=body["type"]))
        pc.addTrack(CameraVideoTrack(camera_id))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        deadline = asyncio.get_running_loop().time() + 8
        while pc.iceGatheringState != "complete" and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.05)
        return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

@app.post("/api/database/leanbots/{leanbot_id}/approval")
async def update_leanbot_approval(leanbot_id: str, request: Request):
    try:
        body = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail="Expected JSON with approval") from error
    approval = body.get("approval") if isinstance(body, dict) else None
    if approval not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Approval must be approved or rejected")
    if approval == "rejected":
        return {"ok": True, "leanbot_id": leanbot_id, "approval": "rejected", "stored": False}
    record = body.get("record")
    if not isinstance(record, dict) or str(record.get("id")) != leanbot_id:
        raise HTTPException(status_code=400, detail="A matching Leanbot record is required for approval")
    try:
        await asyncio.to_thread(save_approved, record)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"ok": True, "leanbot_id": leanbot_id, "approval": "approved", "stored": True}


@app.get("/health/captures")
async def capture_health():
    """Report whether the capture directory and saved JPEGs are available."""
    jpeg_count = sum(
        1
        for path in CAPTURE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
    )

    return {
        "ok": CAPTURE_DIR.is_dir(),
        "directory": str(CAPTURE_DIR),
        "jpeg_count": jpeg_count,
    }


def send_traffic_command(checker_id, state):
    control = context.socket(zmq.REQ)
    control.setsockopt(zmq.LINGER, 0)
    control.setsockopt(zmq.SNDTIMEO, 2000)
    control.setsockopt(zmq.RCVTIMEO, 2000)
    try:
        control.connect("tcp://127.0.0.1:5557")
        control.send_json({
            "command": "set_traffic_state",
            "checker_id": checker_id,
            "state": state,
        })
        return control.recv_json()
    finally:
        control.close(linger=0)


@app.post("/api/traffic-state")
async def update_traffic_state(request: Request):
    """Set a traffic state from the local dashboard."""
    client_host = request.client.host if request.client else ""
    try:
        if not ipaddress.ip_address(client_host).is_loopback:
            raise HTTPException(status_code=403, detail="Local control only")
    except ValueError as error:
        raise HTTPException(status_code=403, detail="Local control only") from error

    try:
        body = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail="Expected JSON with a state") from error

    if (
        not isinstance(body, dict)
        or not isinstance(body.get("checker_id"), str)
        or not isinstance(body.get("state"), str)
    ):
        raise HTTPException(
            status_code=400,
            detail="Expected checker_id and state (RED or GREEN)",
        )

    try:
        result = await asyncio.to_thread(
            send_traffic_command,
            body["checker_id"],
            body["state"],
        )
    except zmq.Again as error:
        raise HTTPException(status_code=503, detail="Traffic broker is unavailable") from error

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "State update failed"))
    return result


# ==========================================
# WEBSOCKET ENDPOINT
# ==========================================

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    clients.add(ws)

    print("[WS] Client connected:", len(clients))

    try:

        while True:
            await ws.receive_text()

    except WebSocketDisconnect:

        print("[WS] Client disconnected")

    except Exception as e:

        print("[WS] Connection error:", repr(e))

    finally:

        clients.discard(ws)

        print("[WS] Active clients:", len(clients))


# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
