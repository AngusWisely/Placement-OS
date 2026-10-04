#!/usr/bin/env python3
"""Start Placement OS if needed, then open it in the default browser."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = 8766
URL = f"http://{HOST}:{PORT}"


def running() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.3):
            return True
    except OSError:
        return False


def main() -> None:
    if not running():
        data = ROOT / "data"
        data.mkdir(parents=True, exist_ok=True)
        log = open(data / "server.log", "ab")
        subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "run.py")],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        for _ in range(30):
            if running():
                break
            time.sleep(0.2)

    webbrowser.open(URL)


if __name__ == "__main__":
    main()
