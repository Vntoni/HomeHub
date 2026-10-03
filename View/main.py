# src/main.py
import os
import sys
import asyncio
import signal
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import qInstallMessageHandler, QTimer, QObject, QEvent
from PySide6.QtQuickControls2 import QQuickStyle
from qasync import QEventLoop

# (opcjonalnie) jeśli masz ten moduł z zasobami
import View.images.images  # noqa: F401

# Windows: zgodnie z Twoim kodem
if sys.platform.startswith("win"):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

def messageHandler(mode, context, message):
    print(f"[QML] {message}")

qInstallMessageHandler(messageHandler)


class ShutdownRequest(QObject):
    """Defer Qt exit until the async application lifecycle has completed."""
    def __init__(self, app):
        super().__init__(app)
        self.requested = asyncio.Event()
        self.windows = []

    def request(self):
        self.requested.set()
        for window in self.windows:
            window.setVisible(False)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Quit:
            self.request()
            return True
        if event.type() == QEvent.Type.Close and watched in self.windows:
            event.ignore()
            self.request()
            return True
        return False

def main(demo=False):
    os.environ["QT_LOGGING_RULES"] = "qt.qml=true; qt.quick=true;"

    QQuickStyle.setStyle("Material")
    app = QGuiApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    shutdown = ShutdownRequest(app)
    app.installEventFilter(shutdown)

    # Ścieżka do QML: gdy PyInstaller binary → sys._MEIPASS/View, gdy dev → View/
    if hasattr(sys, "_MEIPASS"):
        qml_import_path = str(Path(sys._MEIPASS) / "View")
    else:
        # Tryb deweloperski – View/ zawiera folder Example/ z qmldir
        qml_import_path = str(Path(__file__).parent)

    if demo:
        from Compositions.demo import build_demo_backend as build_backend
    else:
        from Compositions.compositions import build_backend

    async def run_application():
        backend = await build_backend()
        try:
            if shutdown.requested.is_set():
                return
            engine = QQmlApplicationEngine()
            engine.rootContext().setContextProperty("backend", backend)
            engine.rootContext().setContextProperty("demoMode", demo)
            engine.quit.connect(shutdown.request)
            engine.addImportPath(qml_import_path)
            engine.loadFromModule("Example", "main")

            if not engine.rootObjects():
                raise RuntimeError("QML application failed to load")
            shutdown.windows = engine.rootObjects()
            backend.register_task(loop.create_task(backend.init_all()))
            await shutdown.requested.wait()
        finally:
            await backend.shutdown()

    previous_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: shutdown.request())
    # Keep Python signal handling responsive while Qt is idle, including cleanup.
    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(250)
    with loop:
        try:
            # One Qt execution: its exit is requested by qasync only after the
            # complete coroutine (including backend cleanup) has returned.
            loop.run_until_complete(run_application())
        finally:
            signal_timer.stop()
            signal.signal(signal.SIGTERM, previous_sigterm)
            app.removeEventFilter(shutdown)
            asyncio.set_event_loop(None)

if __name__ == "__main__":
    # try:
    #     asyncio.run(main())
    # except KeyboardInterrupt:
    #     pass
    main()
