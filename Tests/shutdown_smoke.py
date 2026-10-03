"""Exercise actual Qt entrypoint and SIGTERM in an isolated offline process."""
import os
import signal
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from Compositions import demo
from View import main as entrypoint

created = []
original_build = demo.build_demo_backend


async def build():
    backend = await original_build()
    created.append(backend)
    return backend


class TestApplication(QGuiApplication):
    def __init__(self, args):
        super().__init__(args)
        QTimer.singleShot(700, lambda: os.kill(os.getpid(), signal.SIGTERM))


with patch.object(demo, "build_demo_backend", build), patch.object(entrypoint, "QGuiApplication", TestApplication):
    entrypoint.main(demo=True)
assert len(created) == 1
assert created[0]._shutdown_task.done()
assert not created[0]._shutdown_task.exception()
assert not created[0]._lifecycle_tasks
assert not created[0]._operations._active
print("SIGTERM Qt shutdown passed offline")
