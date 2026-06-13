#!/usr/bin/env python3
"""Drop-in replacement for python3 -m http.server 8080
Also accepts POST /save?name=<filename> with raw body = file bytes.
Run from the career-agent directory:
    python3 save_server.py
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")


class Handler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(self.path)
        if parsed.path != "/save":
            self.send_response(404)
            self.end_headers()
            return
        params = parse_qs(parsed.query)
        raw_name = params.get("name", ["frame.jpg"])[0]
        # Sanitize filename to prevent path traversal (strip directory components)
        name = os.path.basename(raw_name)
        os.makedirs(SAVE_DIR, exist_ok=True)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        out = os.path.join(SAVE_DIR, name)
        # Validate resolved path stays within SAVE_DIR (defense in depth)
        out_real = os.path.realpath(out)
        save_dir_real = os.path.realpath(SAVE_DIR)
        if not out_real.startswith(save_dir_real + os.sep):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid filename")
            return
        with open(out, "wb") as f:
            f.write(body)
        print(f"  saved {len(body)} bytes → {out}")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def end_headers(self):
        self._cors()
        super().end_headers()

    def log_message(self, fmt, *args):
        if "/save" in (args[0] if args else ""):
            print(fmt % args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    os.makedirs(SAVE_DIR, exist_ok=True)
    print(f"Serving on http://localhost:{port}  (POST /save?name=<file> to write frames/)")
    HTTPServer(("", port), Handler).serve_forever()
