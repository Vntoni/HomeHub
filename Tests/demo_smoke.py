"""Full QML startup smoke check; run with QT_QPA_PLATFORM=offscreen.

Uses only demo services and exits automatically. No network is permitted.
"""
import socket
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from View.main import main


def forbidden(*args, **kwargs):
    raise AssertionError("Demo tried to access the network")


socket.socket.connect = forbidden
socket.getaddrinfo = forbidden
original_load = QQmlApplicationEngine.loadFromModule
results = []


def checked_load(engine, *args):
    original_load(engine, *args)

    def verify():
        root = engine.rootObjects()[0]
        results.append(root.property("isReady"))
        results.append("DEMO" in root.property("title"))
        QGuiApplication.instance().quit()

    QTimer.singleShot(1000, verify)


QQmlApplicationEngine.loadFromModule = checked_load
main(demo=True)
assert results == [True, True], results
print("Demo QML startup passed without network access")
