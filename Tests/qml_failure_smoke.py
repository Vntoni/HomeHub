"""QML load failure must still close an already constructed backend."""
from unittest.mock import patch

from Compositions import demo
from View import main as entrypoint

created = []
original_build = demo.build_demo_backend


async def build():
    backend = await original_build()
    created.append(backend)
    return backend


with patch.object(demo, "build_demo_backend", build), patch.object(
        entrypoint.QQmlApplicationEngine, "loadFromModule", lambda *args: None):
    try:
        entrypoint.main(demo=True)
    except RuntimeError as exc:
        assert str(exc) == "QML application failed to load"
    else:
        raise AssertionError("Missing QML load failure")
assert len(created) == 1
assert created[0]._shutdown_task.done()
assert not created[0]._shutdown_task.exception()
print("QML failure cleanup passed offline")
