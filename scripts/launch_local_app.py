#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the local UOAF BMS briefing web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7400)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        time.sleep(0.5)
        webbrowser.open(url)
    os.environ.setdefault("PYTHONUTF8", "1")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "local_app.app:app",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
