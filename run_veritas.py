#!/usr/bin/env python3
"""Start the Veritas broker, API bridge, camera workers, and web UI."""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SERVER_DIR = ROOT / "server"
CLIENT_DIR = ROOT / "client"


def project_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def wait_for_port(port, process, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Broker exited early with code {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for port {port}")


def main():
    parser = argparse.ArgumentParser(
        description="Run the Veritas server, two cameras, and web client."
    )
    parser.add_argument(
        "--topdown-camera",
        default="1",
        help="Camera index, Linux /dev/video path, or 'picamera2' (default: 1)",
    )
    parser.add_argument(
        "--foot-camera",
        default="0",
        help="Camera index, Linux /dev/video path, or 'picamera2' (default: 0)",
    )
    parser.add_argument(
        "--topdown-model",
        default="server/models/16image.pt",
        help="TOPDOWN YOLO model path",
    )
    parser.add_argument(
        "--foot-model",
        default="server/models/16image.pt",
        help="FOOT YOLO model path",
    )
    parser.add_argument(
        "--topdown-warp",
        default="server/tests/topdown.npy",
        help="Optional TOPDOWN perspective warp matrix",
    )
    parser.add_argument(
        "--foot-warp",
        default="server/tests/foot.npy",
        help="FOOT-to-TOPDOWN warp matrix used for Leanbot matching",
    )
    parser.add_argument(
        "--road-sections",
        default="server/road_zones/test.json",
        help="TOPDOWN road-zone JSON file",
    )
    parser.add_argument(
        "--vite-host",
        default="127.0.0.1",
        help="Host for the Vite UI (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--gpio",
        action="store_true",
        help="Enable the six GPIO outputs assigned in server/traffic_checkers.json",
    )
    parser.add_argument(
        "--gpio-active-low",
        action="store_true",
        help="Use active-low module inputs (default is active-high)",
    )
    args = parser.parse_args()

    if (str(args.topdown_camera).strip().isdecimal()
            and str(args.foot_camera).strip().isdecimal()
            and int(args.topdown_camera) == int(args.foot_camera)):
        parser.error(
            "TOPDOWN and FOOT cannot share the same camera index. "
            "Choose the two camera indexes separately, for example "
            "--topdown-camera 1 --foot-camera 0."
        )

    broker_environment = os.environ.copy()
    if args.gpio:
        broker_environment.update({
            "VERITAS_GPIO": "1",
            "VERITAS_GPIO_ACTIVE_HIGH": "0" if args.gpio_active_low else "1",
        })

    topdown_model = project_path(args.topdown_model)
    foot_model = project_path(args.foot_model)
    topdown_warp = project_path(args.topdown_warp)
    foot_warp = project_path(args.foot_warp)
    road_sections = project_path(args.road_sections)

    required_files = [topdown_model, foot_model, foot_warp, road_sections]
    if not topdown_warp.is_file():
        # A TOPDOWN warp is optional in veritascli.py.
        topdown_warp = None

    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        parser.error("Required file(s) not found: " + ", ".join(missing))

    npm = shutil.which("npm")
    if not npm:
        parser.error("npm was not found. Install Node.js and run npm install in client/ first.")
    if not (CLIENT_DIR / "node_modules").is_dir():
        parser.error("client/node_modules is missing. Run `npm install` in client/ first.")

    topdown_command = [
        sys.executable, "veritascli.py", "run",
        "--camera_type", "TOPDOWN",
        "--capture_device", str(args.topdown_camera),
        "--model", str(topdown_model),
        "--road_sections_path", str(road_sections),
    ]
    if topdown_warp is not None:
        topdown_command.extend(["--warp_matrix_path", str(topdown_warp)])

    foot_command = [
        sys.executable, "veritascli.py", "run",
        "--camera_type", "FOOT",
        "--capture_device", str(args.foot_camera),
        "--model", str(foot_model),
        "--road_sections_path", str(road_sections),
        "--warp_matrix_path", str(foot_warp),
    ]

    vite_args = [npm, "run", "dev", "--", "--host", args.vite_host, "--strictPort"]
    if os.name == "nt":
        # npm is commonly installed as npm.cmd on Windows.
        vite_command = subprocess.list2cmdline(vite_args)
        vite_shell = True
    else:
        vite_command = vite_args
        vite_shell = False

    processes = []

    def start(name, command, cwd, shell=False, env=None):
        print(f"[launcher] Starting {name}", flush=True)
        process = subprocess.Popen(command, cwd=str(cwd), shell=shell, env=env)
        processes.append((name, process))
        time.sleep(0.5)
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited early with code {process.returncode}")
        return process

    try:
        broker = start(
            "broker",
            [sys.executable, "veritasbroker.py"],
            SERVER_DIR,
            env=broker_environment,
        )
        wait_for_port(5555, broker)

        start("FastAPI bridge", [sys.executable, "veritasbridge.py"], SERVER_DIR)
        start("web UI", vite_command, CLIENT_DIR, shell=vite_shell)
        start("TOPDOWN camera", topdown_command, SERVER_DIR)
        start("FOOT camera", foot_command, SERVER_DIR)

        print("\n[launcher] Veritas is running. Press Ctrl+C to stop all processes.", flush=True)
        print("[launcher] UI: http://127.0.0.1:5173", flush=True)
        print("[launcher] Capture check: http://127.0.0.1:8000/health/captures", flush=True)

        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    raise RuntimeError(f"{name} exited with code {code}")
                time.sleep(0.25)

    except KeyboardInterrupt:
        print("\n[launcher] Stopping Veritas processes...", flush=True)
    except Exception as error:
        print(f"[launcher] {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)
    finally:
        for name, process in reversed(processes):
            if process.poll() is None:
                if os.name == "nt" and name == "web UI":
                    # npm.cmd runs through a shell; stop its Node child too.
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    process.terminate()
        for name, process in reversed(processes):
            if process.poll() is None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[launcher] Force stopping {name}", flush=True)
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
