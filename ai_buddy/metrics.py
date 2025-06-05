"""Prometheus metrics exporter."""

from __future__ import annotations

import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Tuple


class MetricsHandler(BaseHTTPRequestHandler):
    """Return fake metrics."""

    def do_GET(self) -> None:  # noqa: D401
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        error_rate = random.random() / 50
        latency = random.random() * 0.5
        content = f"http_error_rate {error_rate}\n" f"latency_p95 {latency}\n"
        self.wfile.write(content.encode())


def serve_metrics(addr: Tuple[str, int]) -> None:
    server = HTTPServer(addr, MetricsHandler)
    server.serve_forever()


__all__ = ["serve_metrics"]
