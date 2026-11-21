#!/usr/bin/env python3
"""
========================================================================================
  INTERACTIVE 3D NANOFLUID BATTERY THERMAL MANAGEMENT SYSTEM (BTMS)
  Real-Time 3D Simulation Executable & Master Orchestrator
========================================================================================
Project: Magnetohydrodynamic Hybrid Nanofluid Cooling of Lithium-Ion Batteries:
         A Coupled Porous Medium and Data-Driven Modeling Approach

Features:
  - 50 Individual Battery Cells (B01 - B50) with independent thermal/electrical states
  - Visible 3D Nanoparticles (Al2O3 silver and CuO copper) circulating inside pipelines
  - Real-Time Automatic Temperature Controller with dynamic threshold & hysteresis
  - Full 3D Cooling Loop: Microchannel plates, reservoir, pump, radiator, fan, chiller
  - Live Evaluation of all 24 Governing Mathematical Formulations
  - Interactive 3D Orbit, Zoom, Pan, Exploded View, Raycast Click Inspection
  - CSV/JSON/Excel Dataset Ingestion & Validation
  - ML Surrogate Thermal Predictions (Random Forest, Gradient Boosting, XGBoost, etc.)
========================================================================================
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import sys
import time
import socket
import argparse
import threading
import webbrowser
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_banner():
    banner = """
========================================================================================
   ___ _____ __  __ ____    _____ ____    ____  _                 _       _   _             
  | __|_   _|  \\/  / ___|  |___ /|  _ \\  / ___|(_)_ __ ___  _   _| | __ _| |_(_) ___  _ __  
  |  _ \\ | | | |\\/| \\___ \\    |_ \\| | | | \\___ \\| | '_ ` _ \\| | | | |/ _` | __| |/ _ \\| '_ \\ 
  | |_) || | | |  | |___) |  ___) | |_| |  ___) | | | | | | | |_| | | (_| | |_| | (_) | | | |
  |____/ |_| |_|  |_|____/  |____/|____/  |____/|_|_| |_| |_|\\__,_|_|\\__,_|\\__|_|\\___/|_| |_|
========================================================================================
  Coupled Darcy-Brinkman Porous Media + Magnetohydrodynamic (MHD) Hybrid Nanofluid
  50 Individual Cells (B01-B50) | Moving Al2O3/CuO Nanoparticles | 24 Equations
========================================================================================
"""
    print(banner)


def is_port_available(host: str, port: int) -> bool:
    """Check if a TCP port is available on the specified host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(host: str, starting_port: int, max_attempts: int = 20) -> int:
    """Find the next available TCP port starting from starting_port."""
    for p in range(starting_port, starting_port + max_attempts):
        if is_port_available(host, p):
            return p
    return starting_port


def open_browser_delayed(url: str, delay_seconds: float = 1.2):
    """Wait for server to start, then automatically launch the default browser."""
    def _open():
        time.sleep(delay_seconds)
        print(f"\n[3D BTMS] Launching web browser at: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[3D BTMS] Note: Could not open browser automatically: {e}")
            print(f"[3D BTMS] Please open {url} manually in your browser.")
    
    t = threading.Thread(target=_open, daemon=True)
    t.start()


def main():
    parser = argparse.ArgumentParser(
        description="Launch the Real-Time Interactive 3D BTMS Simulation Application."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run the 3D WebGL application (default: 8080)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the default web browser automatically"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run Flask in debug mode"
    )

    args = parser.parse_args()

    print_banner()

    port = args.port
    if not is_port_available(args.host, port):
        alt_port = find_available_port(args.host, port + 1)
        print(f"[3D BTMS] Port {port} is currently in use. Switching to port {alt_port}.")
        port = alt_port

    target_url = f"http://{args.host}:{port}"

    print(f"[*] Starting 3D BTMS Engine on {target_url}")
    print("[*] Controls Guide:")
    print("    - Left Mouse Click + Drag: Rotate 3D Scene (360 Orbit)")
    print("    - Right Mouse Click + Drag: Pan 3D Camera")
    print("    - Scroll Wheel: Zoom In / Out")
    print("    - Left Click on Cell (B01-B50) or Component: Inspect telemetry & equations")
    print("    - Sliders: Adjust Temperature Threshold, Flow Rate, C-Rate, Magnetic Field")
    print("    - Buttons: Exploded View, Transparent Casing, Reset View, Run/Pause")
    print("=" * 88)

    if not args.no_browser:
        open_browser_delayed(target_url, delay_seconds=1.2)

    try:
        from btms_3d.backend.app import app
        # Run Flask server
        app.run(
            host=args.host,
            port=port,
            debug=args.debug,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n\n[3D BTMS] Shutting down simulation server gracefully. Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[3D BTMS ERROR] Failed to start simulation server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
