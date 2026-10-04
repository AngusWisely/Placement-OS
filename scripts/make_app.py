#!/usr/bin/env python3
"""Build a simple macOS Placement OS launcher app."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "launch.py"
DEST = Path.home() / "Applications" / "Placement OS.app"


def apple_script() -> str:
    command = f"/usr/bin/env python3 {shlex_quote(str(LAUNCHER))} >/dev/null 2>&1 &"
    escaped = command.replace("\\", "\\\\").replace('"', '\\"')
    return f'do shell script "{escaped}"\n'


def shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def main() -> None:
    if platform.system() != "Darwin":
        raise SystemExit("This launcher builder is for macOS.")

    compiler = shutil.which("osacompile")
    if not compiler:
        raise SystemExit("Could not find osacompile on this Mac.")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        shutil.rmtree(DEST)

    script = ROOT / "data" / "placement_os_launcher.applescript"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(apple_script(), encoding="utf-8")

    subprocess.run([compiler, "-o", str(DEST), str(script)], check=True)
    print(f"Created: {DEST}")
    print("Open Finder → Applications, then drag Placement OS to your Dock.")


if __name__ == "__main__":
    main()
