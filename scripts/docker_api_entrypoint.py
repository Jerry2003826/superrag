from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

from ebrag.settings import load_settings


def _database_host_port(database_url: str) -> tuple[str, int]:
    parsed = urlparse(database_url)
    return parsed.hostname or "postgres", parsed.port or 5432


def _wait_for_tcp(host: str, port: int, *, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0):
                return
        except OSError:
            time.sleep(1.0)
    msg = f"Timed out waiting for {host}:{port}"
    raise TimeoutError(msg)


def main() -> None:
    settings = load_settings()
    host, port = _database_host_port(settings.database.url)
    _wait_for_tcp(host, port)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ebrag.api.app:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
    )


if __name__ == "__main__":
    main()
