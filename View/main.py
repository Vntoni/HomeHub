# src/main.py
import os
import sys
import asyncio
import signal
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import qInstallMessageHandler
from qasync import QEventLoop, asyncSlot

# (opcjonalnie) jeśli masz ten moduł z zasobami
import images.images  # noqa: F401

# Windows: zgodnie z Twoim kodem
if sys.platform.startswith("win"):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

def messageHandler(mode, context, message):
    print(f"[QML] {message}")

qInstallMessageHandler(messageHandler)

def main():
    os.environ["QT_LOGGING_RULES"] = "qt.qml=true; qt.quick=true;"

    app = QGuiApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Ścieżka do QML: gdy PyInstaller binary → sys._MEIPASS/View, gdy dev → View/
    if hasattr(sys, "_MEIPASS"):
        qml_import_path = str(Path(sys._MEIPASS) / "View")
    else:
        # Tryb deweloperski – View/ zawiera folder Example/ z qmldir
        qml_import_path = str(Path(__file__).parent)

    from Compositions.compositions import build_backend

    with loop:
        backend = loop.run_until_complete(build_backend())

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", backend)
        engine.addImportPath(qml_import_path)
        engine.loadFromModule("Example", "main")

        if not engine.rootObjects():
            sys.exit(-1)

        loop.create_task(backend.init_all())
        loop.run_forever()

if __name__ == "__main__":
    # try:
    #     asyncio.run(main())
    # except KeyboardInterrupt:
    #     pass
    main()