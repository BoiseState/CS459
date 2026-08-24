"""
CS 459 -- hello world service.

Standard library only, on purpose: this container needs zero dependencies,
so the image builds in seconds and there is nothing to go wrong.

Serves JSON on port 8000:
    GET /        hello + the container's own hostname
    GET /health  liveness check
"""

import json
import os
import socket
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/", "/health"):
            self.send_error(404, "try / or /health")
            return

        body = json.dumps(
            {
                "message": "Hello from inside the container!",
                # Inside a container this is the container ID, not your
                # laptop's name. That's how you know where the code ran.
                "hostname": socket.gethostname(),
                "in_container": os.path.exists("/.dockerenv"),
                "python_version": os.sys.version.split()[0],
                "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            indent=2,
        ).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        # Log to stdout so `docker compose logs` shows requests as they arrive.
        print(f"[{self.address_string()}] {fmt % args}", flush=True)


if __name__ == "__main__":
    # 0.0.0.0, not 127.0.0.1. Binding to localhost inside a container means
    # "reachable only from inside this container," and your port mapping will
    # appear to do nothing. This is the most common Docker networking mistake.
    print(f"Serving on http://0.0.0.0:{PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
