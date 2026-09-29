"""Unified Single-Command Runner for Adaptive 2.5D LiDAR Perception System.
DRDO Problem Statement #26053

Usage:
    python run.py                # Run simulation, open browser, supervise with Ctrl+C
    run.bat                      # Double-click or run from terminal
    python run.py --background   # Run in background (daemon mode)
    python run.py --status       # Check active health of services
    python run.py --stop         # Stop all running simulation services
    python run.py --restart      # Cleanly restart all services
    python run.py --no-browser   # Run without opening the browser
"""
import sys
import os
import time
import socket
import urllib.request
import subprocess
import json
import webbrowser
import signal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
WEB_UI_DIR = ROOT_DIR / "web-ui"
LOGS_DIR = ROOT_DIR / ".logs"
PID_FILE = LOGS_DIR / "running_pids.json"

WS_PORT = 8765
VITE_PORT = 3000
FRONTEND_URL = f"http://localhost:{VITE_PORT}"
BACKEND_WS = f"ws://localhost:{WS_PORT}"


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is actively listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def is_http_ready(url: str, timeout: float = 1.0) -> bool:
    """Check if an HTTP endpoint returns a valid response."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AV-Health-Check"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 304)
    except Exception:
        return False


def get_pids_for_port(port: int) -> set:
    """Retrieve PIDs listening on a given port on Windows."""
    pids = set()
    if os.name == "nt":
        try:
            sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "netstat.exe"
            netstat_cmd = f'"{sys32}" -ano' if sys32.exists() else "netstat -ano"
            out = subprocess.check_output(
                f'{netstat_cmd} | findstr :{port}',
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in line:
                    try:
                        pids.add(int(parts[-1]))
                    except ValueError:
                        pass
        except Exception:
            pass
    return pids


def kill_pids(pids):
    """Terminate given processes safely."""
    for pid in pids:
        if pid <= 4:
            continue
        try:
            if os.name == "nt":
                subprocess.run(f"taskkill /PID {pid} /T /F", shell=True, capture_output=True)
            else:
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def stop_services(quiet: bool = False):
    """Stop all running simulation services."""
    LOGS_DIR.mkdir(exist_ok=True)
    pids_to_kill = set()

    # Read saved PIDs
    if PID_FILE.exists():
        try:
            saved = json.loads(PID_FILE.read_text(encoding="utf-8"))
            for pid in saved.values():
                if isinstance(pid, int):
                    pids_to_kill.add(pid)
        except Exception:
            pass

    # Check port PIDs
    pids_to_kill.update(get_pids_for_port(WS_PORT))
    pids_to_kill.update(get_pids_for_port(VITE_PORT))

    if pids_to_kill:
        if not quiet:
            print(f"[*] Stopping active processes (PIDs: {sorted(list(pids_to_kill))})...")
        kill_pids(pids_to_kill)
        time.sleep(0.8)

    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except Exception:
            pass

    if not quiet:
        print("[OK] All simulation services stopped.")


def check_status() -> bool:
    """Print current status of services."""
    backend_ok = is_port_in_use(WS_PORT)
    frontend_ok = is_port_in_use(VITE_PORT)

    print("==============================================================")
    print("  Adaptive Variable Resolution 2.5D LiDAR Perception System")
    print("  Service Status Check")
    print("==============================================================")
    print(f"  Backend (Python WS): {'RUNNING (ws://localhost:8765)' if backend_ok else 'STOPPED'}")
    print(f"  Frontend (Vite 3D):  {'RUNNING (http://localhost:3000)' if frontend_ok else 'STOPPED'}")
    print("==============================================================")
    return backend_ok and frontend_ok


def start_services(open_browser: bool = True, background: bool = False) -> bool:
    """Start backend and frontend with active health verification."""
    LOGS_DIR.mkdir(exist_ok=True)

    # 1. Check if already running healthy
    if is_port_in_use(WS_PORT) and is_http_ready(FRONTEND_URL):
        print("==============================================================")
        print("  Simulation is ALREADY RUNNING and healthy!")
        print(f"  3D Web UI : {FRONTEND_URL}")
        print(f"  Backend   : {BACKEND_WS}")
        print("==============================================================")
        if open_browser:
            webbrowser.open(FRONTEND_URL)
        return True

    # 2. Clear any zombie instances holding ports
    if is_port_in_use(WS_PORT) or is_port_in_use(VITE_PORT):
        print("[*] Releasing busy ports before fresh launch...")
        stop_services(quiet=True)

    backend_log_file = open(LOGS_DIR / "backend.log", "w", encoding="utf-8")
    frontend_log_file = open(LOGS_DIR / "frontend.log", "w", encoding="utf-8")

    # 3. Launch Backend
    print("[1/2] Initializing Simulation Backend (main.py)...")
    backend_cmd = [sys.executable, "-u", str(ROOT_DIR / "main.py"), "--headless"]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(ROOT_DIR),
        stdout=backend_log_file,
        stderr=subprocess.STDOUT
    )

    # 4. Launch Frontend
    print("[2/2] Initializing 3D Web Visualizer (Vite)...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(WEB_UI_DIR),
        stdout=frontend_log_file,
        stderr=subprocess.STDOUT
    )

    # 5. Active Health Probing (Max 15 seconds)
    print("Waiting for services to become ready...")
    ready_backend = False
    ready_frontend = False

    t_start = time.time()
    while time.time() - t_start < 15.0:
        if not ready_backend and is_port_in_use(WS_PORT):
            ready_backend = True
        if not ready_frontend and (is_http_ready(FRONTEND_URL) or is_port_in_use(VITE_PORT)):
            ready_frontend = True

        if ready_backend and ready_frontend:
            break
        time.sleep(0.4)

    # Record active PIDs
    backend_pids = list(get_pids_for_port(WS_PORT))
    frontend_pids = list(get_pids_for_port(VITE_PORT))
    b_pid = backend_pids[0] if backend_pids else backend_proc.pid
    f_pid = frontend_pids[0] if frontend_pids else frontend_proc.pid
    PID_FILE.write_text(
        json.dumps({"backend": b_pid, "frontend": f_pid}),
        encoding="utf-8"
    )

    if ready_backend and ready_frontend:
        print()
        print("==============================================================")
        print("  Adaptive Variable Resolution 2.5D LiDAR Perception System")
        print("  DRDO Problem Statement #26053 - Official Simulation Runner")
        print("==============================================================")
        print(f"  3D Web Interface : {FRONTEND_URL}")
        print(f"  LiDAR Data Feed  : {BACKEND_WS}")
        print(f"  Background Logs  : {LOGS_DIR}\\")
        print("==============================================================")

        if open_browser:
            time.sleep(0.5)
            webbrowser.open(FRONTEND_URL)

        if background:
            print("  Simulation running in background.")
            print("  Use 'python run.py --status' to inspect.")
            print("  Use 'python run.py --stop' to terminate.")
            print("==============================================================")
            return True

        # Foreground Supervisor loop
        print("  Simulation is ACTIVE. Press Ctrl+C to terminate cleanly.")
        print("==============================================================")
        try:
            while True:
                # Check if any child died unexpectedly
                if backend_proc.poll() is not None:
                    print("\n[!] Backend stopped unexpectedly. Inspect .logs/backend.log")
                    break
                if frontend_proc.poll() is not None:
                    print("\n[!] Frontend stopped unexpectedly. Inspect .logs/frontend.log")
                    break
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nStopping simulation services...")
        finally:
            kill_pids([backend_proc.pid, frontend_proc.pid])
            stop_services(quiet=True)
            backend_log_file.close()
            frontend_log_file.close()
            print("[OK] All simulation services stopped cleanly.")
        return True
    else:
        print("\n[WARNING] Timed out waiting for some services:")
        print(f"  Backend (ws://8765):  {'READY' if ready_backend else 'NOT RESPONDING (Check .logs/backend.log)'}")
        print(f"  Frontend (port 3000): {'READY' if ready_frontend else 'NOT RESPONDING (Check .logs/frontend.log)'}")
        stop_services(quiet=True)
        backend_log_file.close()
        frontend_log_file.close()
        return False


def main():
    args = sys.argv[1:]
    if "--stop" in args:
        stop_services()
    elif "--status" in args:
        check_status()
    elif "--restart" in args:
        stop_services()
        time.sleep(0.5)
        start_services()
    else:
        start_services(
            open_browser="--no-browser" not in args,
            background="--background" in args or "-d" in args
        )


if __name__ == "__main__":
    main()
