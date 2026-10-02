"""Real QML + real Airstage SDK with an independent, offline device state."""
import asyncio
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPointF, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from qasync import QEventLoop
from pyairstage.airstageAC import AirstageAC
from pyairstage.constants import ACParameter

from Adapters.airstage_ac_adapter import AirstageACAdapter
from App.climate_service import ClimateService, confirm_ac_power
from Compositions.demo import build_demo_backend
import Interface.qt_backend as backend_module
import View.images.images  # noqa: F401


class FakeCloud:
    def __init__(self):
        self.physical = {"Salon": "0", "Jadalnia": "0"}
        self.fail_read = False
        self.apply_write = False
        self.gate = asyncio.Event()
        self.gate.set()
        self.written = asyncio.Event()
        self.writes = []

    async def set_parameter(self, device, name, value):
        self.writes.append((device, name, value))
        if self.apply_write:
            self.physical[device] = str(int(value))
        self.written.set()
        return 0  # Accepted by transport, not proof the device changed.

    async def get_devices(self):
        await self.gate.wait()
        if self.fail_read:
            raise ConnectionError("fake readback failure")
        return deepcopy({room: {"connectionStatus": "Online", "parameters": [
            {"name": ACParameter.ONOFF_MODE.value, "value": power},
            {"name": ACParameter.OPERATION_MODE.value, "value": "4"},
            {"name": ACParameter.INDOOR_TEMPERATURE.value, "value": "7150"},
            {"name": ACParameter.TARGET_TEMPERATURE.value, "value": "220"},
        ]} for room, power in self.physical.items()})


def find(parent, name):
    pending, visited = [parent], set()
    while pending:
        item = pending.pop()
        if item in visited:
            continue
        visited.add(item)
        if item.objectName() == name:
            return item
        pending.extend(item.children())
        if isinstance(item, QQuickItem):
            pending.extend(item.childItems())
    raise AssertionError(name)


async def fast_readback(service, room, on):
    await confirm_ac_power(service, room, on, interval=0)


async def wait_until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(0.01)


async def run():
    backend = await build_demo_backend()
    cloud = FakeCloud()
    backend._climate = ClimateService({room: AirstageACAdapter(room, cloud, AirstageAC)
                                      for room in cloud.physical})
    backend_module.confirm_ac_power = fast_readback
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("demoMode", True)
    engine.addImportPath(str(Path(__file__).resolve().parents[1] / "View"))
    engine.loadFromModule("Example", "main")
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    finished = asyncio.Event()
    backend.devicePowerFinished.connect(lambda *args: finished.set())
    try:
        await backend.init_all()
        await backend.publish_dashboard()
        await asyncio.sleep(0.2)
        card = find(window, "card_Salon")
        other = find(window, "card_Jadalnia")
        switch = find(card, "devicePower")
        assert not card.property("powered") and not switch.property("checked")
        cloud.gate.clear()
        cloud.fail_read = True
        point = switch.mapToScene(QPointF(switch.width() / 2, switch.height() / 2)).toPoint()
        loop.call_soon(lambda: QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point))
        await asyncio.wait_for(cloud.written.wait(), 2)
        assert card.property("busy") and not switch.property("checked")
        cloud.gate.set()
        await asyncio.wait_for(finished.wait(), 2)
        await backend.publish_dashboard()
        assert not card.property("busy") and card.property("failed")
        assert card.property("message")
        assert not card.property("powered") and not switch.property("checked")
        assert cloud.physical["Salon"] == "0"
        assert not other.property("powered")

        # A later fresh reading updates the real UI without pressing Refresh.
        cloud.fail_read = False
        cloud.physical["Salon"] = "1"
        await backend._climate.refresh("Salon")
        await backend.publish_dashboard()
        assert card.property("powered") and switch.property("checked")

        finished.clear()
        cloud.apply_write = True
        loop.call_soon(lambda: QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point))
        await asyncio.wait_for(finished.wait(), 2)
        # Completion is emitted just before the final dashboard publication.
        await wait_until(lambda: not card.property("powered") and not switch.property("checked"))
        assert not card.property("powered") and not switch.property("checked")
        assert not card.property("failed") and not card.property("busy")
        assert cloud.physical["Salon"] == "0"
        assert len(cloud.writes) == 2
        assert not other.property("powered")
        errors = [w for w in warnings if "Populating font family aliases" not in w]
        assert not errors, errors
        print("AC QML readback passed: pending, failure, retained state, recovery, OFF and room isolation")
    finally:
        cloud.gate.set()
        await backend.shutdown()
        engine.clearComponentCache()


warnings = []
qInstallMessageHandler(lambda mode, context, message: warnings.append(message))
QQuickStyle.setStyle("Material")
app = QGuiApplication([])
loop = QEventLoop(app)
asyncio.set_event_loop(loop)
with loop:
    loop.run_until_complete(run())
