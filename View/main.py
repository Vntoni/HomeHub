# src/main.py
import os
import sys
import asyncio
import signal
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import qInstallMessageHandler, QTimer
from PySide6.QtQuickControls2 import QQuickStyle
from qasync import QEventLoop, asyncSlot

# (opcjonalnie) jeśli masz ten moduł z zasobami
import View.images.images  # noqa: F401

# Windows: zgodnie z Twoim kodem
if sys.platform.startswith("win"):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

def messageHandler(mode, context, message):
    print(f"[QML] {message}")

qInstallMessageHandler(messageHandler)

def main(demo=False):
    os.environ["QT_LOGGING_RULES"] = "qt.qml=true; qt.quick=true;"

    QQuickStyle.setStyle("Material")
    app = QGuiApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

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

    with loop:
        backend = loop.run_until_complete(build_backend())

        previous_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, lambda *_: app.quit())
        # Give Python regular execution time while Qt is idle to handle SIGTERM.
        signal_timer = QTimer()
        signal_timer.timeout.connect(lambda: None)
        signal_timer.start(250)
        try:
            engine = QQmlApplicationEngine()
            engine.rootContext().setContextProperty("backend", backend)
            engine.rootContext().setContextProperty("demoMode", demo)
            engine.quit.connect(app.quit)
            engine.addImportPath(qml_import_path)
            engine.loadFromModule("Example", "main")

            if not engine.rootObjects():
                raise RuntimeError("QML application failed to load")

            backend.register_task(loop.create_task(backend.init_all()))
            loop.run_forever()
        finally:
            signal_timer.stop()
            signal.signal(signal.SIGTERM, previous_sigterm)
            loop.run_until_complete(backend.shutdown())

if __name__ == "__main__":
    # try:
    #     asyncio.run(main())
    # except KeyboardInterrupt:
    #     pass
    main()
