
import asyncio
import ipaddress
import threading
import zmq
import json
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn


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

                future = asyncio.run_coroutine_threadsafe(
                    broadcast_frame(
                        camera_id.decode("utf-8"),
                        frame_bytes
                    ),
                    loop
                )

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
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):[0-9]+$",
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
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


def send_traffic_command(state):
    control = context.socket(zmq.REQ)
    control.setsockopt(zmq.LINGER, 0)
    control.setsockopt(zmq.SNDTIMEO, 2000)
    control.setsockopt(zmq.RCVTIMEO, 2000)
    try:
        control.connect("tcp://127.0.0.1:5557")
        control.send_json({
            "command": "set_traffic_state",
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

    if not isinstance(body, dict) or not isinstance(body.get("state"), str):
        raise HTTPException(status_code=400, detail="Expected state: RED, YELLOW, or GREEN")

    try:
        result = await asyncio.to_thread(send_traffic_command, body["state"])
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
