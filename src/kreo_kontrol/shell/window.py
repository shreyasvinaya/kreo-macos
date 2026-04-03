"""Desktop window for the embedded configurator UI."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Top-level application window for the configurator."""

    def __init__(self, url: str) -> None:
        super().__init__()

        self.setWindowTitle("Kreo Kontrol")
        self.resize(1480, 980)

        view = QWebEngineView(self)
        view.setUrl(QUrl(url))
        self.setCentralWidget(view)
