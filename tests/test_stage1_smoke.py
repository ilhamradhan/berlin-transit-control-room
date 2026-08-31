import fcntl
import json
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "stage1_smoke.py"


class FeedHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"gtfs-realtime-sample"
        self.send_response(200)
        self.send_header("Content-Type", "application/protobuf")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class SlowFeedHandler(FeedHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/protobuf")
        self.end_headers()
        self.wfile.write(b"a")
        self.wfile.flush()
        time.sleep(0.2)
        self.wfile.write(b"b")


class Stage1SmokeTest(unittest.TestCase):
    def test_fetch_emits_aggregate_status_without_retaining_payload(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        lock_path = Path(directory.name) / "lock"
        server = HTTPServer(("127.0.0.1", 0), FeedHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--url",
                f"http://127.0.0.1:{server.server_port}/data",
                "--lock",
                str(lock_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(result.stdout)
        self.assertEqual(status["result"], "ok")
        self.assertEqual(status["bytes"], len(b"gtfs-realtime-sample"))
        self.assertEqual(status["content_type"], "application/protobuf")
        self.assertNotIn("payload", status)
        self.assertEqual(stat.S_IMODE(lock_path.stat().st_mode), 0o600)

    def test_second_run_is_blocked_while_lock_is_held(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        lock_path = Path(directory.name) / "lock"
        with lock_path.open("x") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--url",
                    "http://127.0.0.1:9/",
                    "--lock",
                    str(lock_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 75)
        self.assertEqual(json.loads(result.stderr)["result"], "overlap_blocked")

    def test_symlink_lock_does_not_truncate_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.write_text("keep")
            lock_path = Path(directory) / "lock"
            lock_path.symlink_to(target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--url",
                    "http://127.0.0.1:9/",
                    "--lock",
                    str(lock_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), "keep")
            self.assertEqual(json.loads(result.stderr)["result"], "error")

    def test_invalid_argument_emits_json_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--unknown"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)["result"], "error")

    def test_trickling_response_hits_wall_clock_deadline(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        lock_path = Path(directory.name) / "lock"
        server = HTTPServer(("127.0.0.1", 0), SlowFeedHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--url",
                f"http://127.0.0.1:{server.server_port}/data",
                "--lock",
                str(lock_path),
                "--timeout",
                "0.05",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("deadline", json.loads(result.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
