"""Exercise actual Qt entrypoint and SIGTERM in an isolated offline process."""
import os
import signal
import asyncio
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlExpression
from Compositions import demo
from View import main as entrypoint

created = []
closed = []
original_build = demo.build_demo_backend
trigger = globals().get("TRIGGER", "signal")
fail_cleanup = globals().get("FAIL_CLEANUP", False)
cancelled = []


async def build():
    backend = await original_build()
    class LastResource:
        async def aclose(self):
            closed.append("last")
    class SlowResource:
        async def aclose(self):
            # A repeated close while cleanup awaits must not stop qasync.
            QTimer.singleShot(10, QGuiApplication.instance().quit)
            await asyncio.sleep(.15)
            closed.append("slow")
            if fail_cleanup:
                raise ValueError("fake cleanup failure")
    backend.register_resource(LastResource())
    backend.register_resource(SlowResource())
    async def background():
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.append(True)
    backend.register_task(asyncio.create_task(background()))
    created.append(backend)
    return backend


original_load = entrypoint.QQmlApplicationEngine.loadFromModule


def load(engine, *args):
    original_load(engine, *args)
    def close():
        if trigger == "signal":
            os.kill(os.getpid(), signal.SIGTERM)
        elif trigger == "window":
            engine.rootObjects()[0].close()
        else:
            expression = QQmlExpression(engine.rootContext(), engine.rootObjects()[0], "Qt.quit()")
            expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
    QTimer.singleShot(100, close)


with patch.object(demo, "build_demo_backend", build), patch.object(entrypoint.QQmlApplicationEngine, "loadFromModule", load):
    try:
        entrypoint.main(demo=True)
    except ExceptionGroup as exc:
        assert fail_cleanup
        assert len(exc.exceptions) == 1
        assert isinstance(exc.exceptions[0], ValueError)
        assert str(exc.exceptions[0]) == "fake cleanup failure"
    else:
        assert not fail_cleanup, "Cleanup error was hidden"
assert len(created) == 1
assert created[0]._shutdown_task.done()
assert bool(created[0]._shutdown_task.exception()) == fail_cleanup
assert not created[0]._lifecycle_tasks
assert not created[0]._operations._active
assert closed == ["slow", "last"]
assert cancelled == [True]
assert signal.getsignal(signal.SIGTERM) == signal.SIG_DFL
print(f"Qt shutdown passed offline: {trigger}, cleanup_error={fail_cleanup}")
