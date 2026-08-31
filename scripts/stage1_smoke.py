#!/usr/bin/env python3
import argparse
import fcntl
import json
import os
import shutil
import signal
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIN_AVAILABLE_MEMORY = 512 * 1024 * 1024
MIN_AVAILABLE_DISK = 4 * 1024 * 1024 * 1024
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
DEFAULT_URL = "https://production.gtfsrt.vbb.de/data"
DEFAULT_LOCK = ROOT / "state" / "stage1-smoke.lock"


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def available_memory():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable is missing from /proc/meminfo")


def deadline_exceeded(signum, frame):
    raise TimeoutError("response deadline exceeded")


def main():
    parser = ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if args.timeout <= 0:
        raise ValueError("timeout must be positive")

    memory = available_memory()
    disk = shutil.disk_usage(ROOT).free
    if memory < MIN_AVAILABLE_MEMORY:
        raise RuntimeError("available memory is below 512 MiB")
    if disk < MIN_AVAILABLE_DISK:
        raise RuntimeError("available disk is below the 4 GiB collection cap")

    lock_path = Path(args.lock)
    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "r+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"result": "overlap_blocked"}), file=sys.stderr)
            return 75

        request = urllib.request.Request(
            args.url, headers={"User-Agent": "TransitOpsBerlinStage1/0.1"}
        )
        previous_handler = signal.signal(signal.SIGALRM, deadline_exceeded)
        signal.setitimer(signal.ITIMER_REAL, args.timeout)
        try:
            with urllib.request.urlopen(request, timeout=min(args.timeout, 30)) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                content_type = response.headers.get_content_type()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)

        if not payload:
            raise RuntimeError("VBB response was empty")
        if len(payload) > MAX_RESPONSE_BYTES:
            raise RuntimeError("VBB response exceeded 64 MiB")
        if content_type != "application/protobuf":
            raise RuntimeError(f"unexpected content type: {content_type}")

        print(
            json.dumps(
                {
                    "result": "ok",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "bytes": len(payload),
                    "content_type": content_type,
                    "available_memory_bytes": memory,
                    "available_disk_bytes": disk,
                }
            )
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({"result": "error", "error": str(error)}), file=sys.stderr)
        sys.exit(1)
