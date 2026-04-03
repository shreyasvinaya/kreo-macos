"""Application entrypoints for the Kreo Swarm configurator."""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from threading import Thread

from uvicorn import Config, Server

from kreo_kontrol.api.app import create_app
from kreo_kontrol.device.bytech_lighting import build_default_lighting_controller


def build_app_url(port: int) -> str:
    """Build the loopback URL used by the embedded UI shell."""

    return f"http://127.0.0.1:{port}"


def find_free_loopback_port() -> int:
    """Reserve and release a free loopback port for the local server."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_server_config(port: int, frontend_dist: Path | None = None) -> Config:
    """Create the loopback Uvicorn configuration for the desktop shell."""

    return Config(
        app=create_app(
            frontend_dist=frontend_dist,
            lighting_controller=build_default_lighting_controller(),
        ),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


def start_server_thread(server: Server) -> Thread:
    """Start the loopback API server on a background daemon thread."""

    thread = Thread(target=server.run, daemon=True, name="kreo-kontrol-server")
    thread.start()
    return thread


def main() -> int:
    """Run the desktop shell and embedded loopback backend."""

    from PySide6.QtWidgets import QApplication

    from kreo_kontrol.shell.window import MainWindow

    port = find_free_loopback_port()
    config = build_server_config(port)
    server = Server(config)
    server_thread = start_server_thread(server)

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(build_app_url(port))
    window.show()

    try:
        return int(app.exec())
    finally:
        server.should_exit = True
        server_thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
