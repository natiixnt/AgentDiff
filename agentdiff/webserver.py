from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class AgentDiffRequestHandler(BaseHTTPRequestHandler):
    analysis: dict[str, Any] = {}
    static_root: Path = Path.cwd()

    def _send_bytes(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_static(self, target: str) -> None:
        safe_target = target.lstrip("/")
        if not safe_target:
            safe_target = "index.html"

        file_path = (self.static_root / safe_target).resolve()
        if not str(file_path).startswith(str(self.static_root.resolve())) or not file_path.exists():
            self._send_bytes(b"Not Found", "text/plain; charset=utf-8", status=HTTPStatus.NOT_FOUND)
            return

        payload = file_path.read_bytes()
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self._send_bytes(payload, content_type)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/analysis":
            payload = json.dumps(self.analysis, indent=2).encode("utf-8")
            self._send_bytes(payload, "application/json; charset=utf-8")
            return

        if self.path in {"/", "/index.html", "/styles.css", "/app.js"}:
            target = "index.html" if self.path in {"/", "/index.html"} else self.path[1:]
            self._serve_static(target)
            return

        self._send_bytes(b"Not Found", "text/plain; charset=utf-8", status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Keep console output focused on explicit startup logs.
        return


def run_server(analysis: dict[str, Any], host: str = "127.0.0.1", port: int = 8765) -> None:
    static_root = Path(__file__).resolve().parent.parent / "web"

    handler_cls = type(
        "ConfiguredAgentDiffHandler",
        (AgentDiffRequestHandler,),
        {"analysis": analysis, "static_root": static_root},
    )

    server = ThreadingHTTPServer((host, port), handler_cls)
    print(f"AgentDiff web UI: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
