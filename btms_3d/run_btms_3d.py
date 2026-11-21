#!/usr/bin/env python3
"""
Interactive 3D BTMS Simulation Application Launcher
Starts the Flask server hosting the 3D WebGL Three.js interface,
numerical physics engine, 24 governing equations, and ML surrogate models.
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import sys
import argparse
import webbrowser
import threading
import time

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from btms_3d.backend.app import app


def print_banner(host: str, port: int):
    banner = f"""
========================================================================================
   INTERACTIVE 3D MHD HYBRID NANOFLUID BATTERY THERMAL MANAGEMENT SYSTEM (BTMS)
========================================================================================
  Continuous Operation & Intelligent Nanofluid Cooling Digital Twin
  WebGL / Three.js Real-Time Engineering Visualization
========================================================================================
  * 600+ Individual Cylindrical Li-ion Cells (21700 / 18650, CELL-001 to CELL-600)
  * Continuous Battery Pack Operation with Repeated Localized Overheating Events
  * Hotspot Configurations A to H (Single, Double, Cluster, Multi-Zone, Patterns)
  * Trumony Wavy/Scalloped Metallic Cooling Ribbons & Balanced Parallel Kirchhoff Network
  * Closed-Loop Nanofluid & Nanoparticle Circulation (Al2O3 + Cu Hybrid)
  * Magnetohydrodynamic (MHD) Transverse Field & Darcy-Brinkman Porous Media
  * Temperature Uniformity Tracking (Target: ΔT = T_max - T_min < 5.0 K)
  * BMS Power Derating Protection (Triggered at T_max ≥ 55°C)
  * Full Hotspot Lifecycle Audit Trail with Real-Time Event History & CSV Export
  * 10 In-Line Pipeline Measurement Points (P01 - P10) & 39 Governing Equations
========================================================================================
  [SERVER RUNNING] Web Application URL: http://{host}:{port}/
  Press Ctrl+C to terminate the server.
========================================================================================
"""
    print(banner)


def open_browser_delayed(url: str, delay: float = 1.0):
    def _open():
        time.sleep(delay)
        print(f"\n[BTMS-3D] Opening browser at {url}...")
        webbrowser.open(url)
    t = threading.Thread(target=_open, daemon=True)
    t.start()


def main():
    parser = argparse.ArgumentParser(description="Launch Interactive 3D BTMS Simulation")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Binding host IP")
    parser.add_argument("--port", type=int, default=5001, help="Server port number (default: 5001)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    parser.add_argument("--debug", action="store_true", help="Run Flask in debug mode")

    args = parser.parse_args()

    port = int(os.environ.get("PORT", args.port))
    host = args.host
    url = f"http://{host}:{port}"

    print_banner(host, port)

    if not args.no_browser and not os.environ.get("NO_BROWSER"):
        open_browser_delayed(url, delay=0.8)

    try:
        app.run(host=host, port=port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n[BTMS-3D] Server gracefully shutdown. Goodbye!")


if __name__ == "__main__":
    main()
