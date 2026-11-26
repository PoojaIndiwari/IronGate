"""A read-only teaching API for fictional PayNest payments."""
import argparse
import json
import sqlite3
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit


def payment(reference):
    # A fresh in-memory database keeps the sample deterministic on every laptop.
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE payment (reference TEXT PRIMARY KEY, cents INTEGER)")
        db.execute("INSERT INTO payment VALUES (?, ?)", ("demo-001", 2500))
        return db.execute(
            "SELECT reference, cents FROM payment WHERE reference = ?", (reference,)
        ).fetchone()


def lookup(path):
    if path == "/health":
        return HTTPStatus.OK, {"status": "ok"}
    if path.startswith("/payments/"):
        result = payment(unquote(path.removeprefix("/payments/")))
        if result:
            return HTTPStatus.OK, {"reference": result[0], "amount_cents": result[1], "currency": "LKR"}
    return HTTPStatus.NOT_FOUND, {"error": "not found"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, payload = lookup(urlsplit(self.path).path)
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with ThreadingHTTPServer((args.host, args.port), Handler) as server:
        server.serve_forever()
