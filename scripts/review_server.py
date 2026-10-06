#!/usr/bin/env python3
"""Local FPL Vortex review server.

Serves the static review site and mirrors the Cloudflare `/api/manager`
endpoint so My Team Lab can be tested locally with only Python 3.
No manager data is written to disk.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FPL_BASE = "https://fantasy.premierleague.com/api"
HOST = "127.0.0.1"
DEFAULT_PORT = 8080
USER_AGENT = "FPL-Vortex-Local-Review/1.0"


def fetch_json(path: str) -> dict:
    request = Request(
        f"{FPL_BASE}{path}",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as exc:
        error = RuntimeError(f"FPL API {exc.code}")
        error.status = exc.code  # type: ignore[attr-defined]
        raise error from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        error = RuntimeError("Could not reach the official FPL API")
        error.status = 502  # type: ignore[attr-defined]
        raise error from exc


class ReviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        if parsed.path == "/api/manager":
            self.handle_manager(parsed.query)
            return
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "mode": "local-review"})
            return
        super().do_GET()

    def handle_manager(self, query: str) -> None:
        params = parse_qs(query)
        entry = (params.get("entry", [""])[0] or "").strip()
        if not entry.isdigit() or not 1 <= len(entry) <= 10:
            self.send_json({"error": "A numeric FPL entry ID is required."}, HTTPStatus.BAD_REQUEST)
            return

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                summary_future = pool.submit(fetch_json, f"/entry/{entry}/")
                history_future = pool.submit(fetch_json, f"/entry/{entry}/history/")
                summary = summary_future.result()
                history = history_future.result()

            requested_gw = (params.get("gw", [""])[0] or "").strip()
            if requested_gw.isdigit() and int(requested_gw) > 0:
                current_gw = int(requested_gw)
            else:
                current_gw = int(summary.get("current_event") or 1)

            picks = fetch_json(f"/entry/{entry}/event/{current_gw}/picks/")
            live = fetch_json(f"/event/{current_gw}/live/")
            self.send_json(
                {
                    "entry": int(entry),
                    "gw": current_gw,
                    "summary": summary,
                    "history": history,
                    "picks": picks,
                    "live": live,
                }
            )
        except Exception as exc:  # keep local review response aligned with hosted API
            status = int(getattr(exc, "status", 502) or 502)
            if status == 404:
                message = "FPL manager not found."
            else:
                message = "Could not reach the official FPL API."
            self.send_json({"error": message, "status": status}, status)


def main() -> None:
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            raise SystemExit("Port must be a number, for example: python3 scripts/review_server.py 8080")

    server = ThreadingHTTPServer((HOST, port), ReviewHandler)
    print("FPL VORTEX local review server")
    print(f"Open: http://{HOST}:{port}")
    print("My Team Lab API: enabled")
    print("Press Control+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping review server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
