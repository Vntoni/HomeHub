# src/main.py
import os
import sys
import asyncio
import signal

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
    # Poprawka: nie nadpisuj jednej zmiennej dwukrotnie
    os.environ["QT_LOGGING_RULES"] = "qt.qml=true; qt.quick=true;"

    app = QGuiApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # === Nowość: budujemy backend wg SOLID (Qt adapter + serwisy + adaptery) ===
    from Compositions.compositions import build_backend  # <- patrz kod poniżej

    # Po załadowaniu QML odpal odświeżenie inicjalne (asynchronicznie)
    with loop:
        backend = loop.run_until_complete(build_backend())  # zwraca QtHomeBackend (QObject)

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", backend)
        engine.addImportPath(sys.path[0])
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