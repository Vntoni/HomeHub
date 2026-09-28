"""Offline Qt interaction and layout check. Optional screenshot directory argument.

QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python Tests/ui_smoke.py /tmp/homehub-ui
"""
import asyncio
from pathlib import Path
import socket
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QObject, QPointF, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from qasync import QEventLoop
from Compositions.demo import build_demo_backend
import View.images.images  # noqa: F401


def forbidden(*args, **kwargs):
    raise AssertionError("UI smoke test attempted network access")


socket.socket.connect = forbidden
socket.getaddrinfo = forbidden
warnings = []
qInstallMessageHandler(lambda mode, context, message: warnings.append(message))
QQuickStyle.setStyle("Material")
app = QGuiApplication([])
loop = QEventLoop(app)
asyncio.set_event_loop(loop)
engine = QQmlApplicationEngine()
output = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if output:
    output.mkdir(parents=True, exist_ok=True)


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
        elif hasattr(item, "contentItem") and callable(item.contentItem):
            pending.append(item.contentItem())
    raise AssertionError((name, warnings))


async def click(window, item):
    assert item.property("enabled"), item.objectName()
    ancestor = item.parentItem()
    while ancestor:
        if ancestor.inherits("QQuickFlickable"):
            local = item.mapToItem(ancestor.property("contentItem"), QPointF(item.width() / 2, item.height() / 2))
            limit = max(0, ancestor.property("contentHeight") - ancestor.height())
            ancestor.setProperty("contentY", max(0, min(limit, local.y() - ancestor.height() / 2)))
            await asyncio.sleep(0.05)
        ancestor = ancestor.parentItem()
    point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    loop.call_soon(lambda: QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point))
    await asyncio.sleep(0.25)


def screenshot(window, name):
    if output:
        assert window.grabWindow().save(str(output / (name + ".png")))


async def run():
    backend = await build_demo_backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("demoMode", True)
    engine.addImportPath(str(Path(__file__).resolve().parents[1] / "View"))
    engine.loadFromModule("Example", "main")
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    await backend.init_all()
    await asyncio.sleep(0.4)
    assert window.property("isReady")
    screenshot(window, "00-start")
    salon = find(window, "card_Salon")
    assert salon.property("targetTemperature") == 22.0
    screenshot(window, "01-parter")
    await click(window, find(window, "openMap"))
    temperature_map = find(window, "temperatureMap")
    assert temperature_map.property("opened")
    await click(window, find(temperature_map, "closeMap"))

    await click(window, find(salon, "deviceSettings"))
    ac = find(window, "acPopup")
    assert ac.property("opened") and ac.property("loaded"), warnings
    assert ac.property("selectedFanSpeed") == "AUTO"
    await click(window, find(ac, "fanSpeed_AUTO"))
    assert find(ac, "fanSpeed_AUTO").property("checked")
    await click(window, find(ac, "temperaturePlus"))
    await click(window, find(ac, "fanSpeed_QUIET"))
    # An unrelated boiler update cannot overwrite the AC draft.
    backend.targetTemperatureReceived.emit("boiler", 65.0)
    screenshot(window, "02-klimatyzacja")
    await click(window, find(ac, "applySettings"))
    assert backend._climate.target_temp("Salon") == 22.5
    assert backend._climate.fan_speed("Salon") == "QUIET"
    assert ac.property("currentFanSpeed") == "QUIET"
    assert not ac.property("saving") and not ac.property("failed")
    assert salon.property("targetTemperature") == 22.5
    screenshot(window, "03-wynik-zapisu")
    await click(window, find(ac, "closeSettings"))
    await click(window, find(salon, "deviceSettings"))
    assert ac.property("selectedFanSpeed") == "QUIET"
    for speed in ["LOW", "MEDIUM", "HIGH", "AUTO"]:
        await click(window, find(ac, "fanSpeed_" + speed))
        await click(window, find(ac, "applySettings"))
        assert backend._climate.fan_speed("Salon") == speed
        assert ac.property("currentFanSpeed") == speed
    await click(window, find(ac, "acMode_FAN"))
    assert not find(ac, "temperaturePlus").property("enabled")
    await click(window, find(ac, "fanSpeed_HIGH"))
    await click(window, find(ac, "applySettings"))
    assert backend._climate.operating_mode("Salon") == "FAN"
    assert backend._climate.fan_speed("Salon") == "HIGH"
    await click(window, find(ac, "closeSettings"))
    await click(window, find(find(window, "card_Jadalnia"), "deviceSettings"))
    assert ac.property("selectedFanSpeed") == "AUTO"
    await click(window, find(ac, "closeSettings"))

    await click(window, find(find(window, "card_boiler"), "deviceSettings"))
    boiler = find(window, "boilerPopup")
    assert boiler.property("loaded")
    screenshot(window, "04-ciepla-woda")
    await click(window, find(boiler, "temperaturePlus"))
    await click(window, find(boiler, "applySettings"))
    assert backend._boiler.get_target_temp() == 55.5
    await click(window, find(boiler, "closeSettings"))

    await click(window, find(window, "upstairsTab"))
    julia = find(window, "card_Julia")
    assert not julia.property("powered")
    await click(window, find(julia, "devicePower"))
    assert backend._heater.get_power("Julia")
    screenshot(window, "05-pietro")
    await click(window, find(julia, "deviceSettings"))
    heater = find(window, "heaterPopup")
    assert heater.property("loaded")
    screenshot(window, "06-grzejnik")
    await click(window, find(heater, "temperaturePlus"))
    await click(window, find(heater, "applySettings"))
    assert backend._heater.get_target_temp("Julia") == 21.5
    async def reject(*args):
        raise RuntimeError("simulated failure")
    original = backend._heater.set_mode
    backend._heater.set_mode = reject
    await click(window, find(heater, "applySettings"))
    assert heater.property("failed") and not heater.property("saving")
    assert heater.property("opened") and heater.property("message")
    screenshot(window, "06b-blad-zapisu")
    backend._heater.set_mode = original
    await click(window, find(heater, "closeSettings"))

    backend.washerOnlineChanged.emit(True)
    backend.washerRemainingChanged.emit(42)
    assert find(window, "washerStatusText").property("text") == "Pozostało 42 min"
    backend.washerOnlineChanged.emit(False)
    assert find(window, "washerStatusText").property("text") == "Brak połączenia"
    backend.washerOnlineChanged.emit(True)
    backend.washerRemainingChanged.emit(0)
    assert find(window, "washerStatusText").property("text") == "Nieaktywna"

    for width, height in [(1280, 720), (800, 480), (720, 1280)]:
        window.resize(width, height)
        await asyncio.sleep(0.3)
        screenshot(window, f"07-layout-{width}x{height}")
        if width >= 840:
            await click(window, find(julia, "deviceSettings"))
        # At narrow sizes the third card is below the fold; open a visible card.
        if width < 840:
            await click(window, find(find(window, "card_Juras"), "deviceSettings"))
        assert heater.property("opened")
        assert heater.property("width") <= width and heater.property("height") <= height
        screenshot(window, f"08-popup-{width}x{height}")
        await click(window, find(heater, "closeSettings"))
        await click(window, find(window, "downstairsTab"))
        await click(window, find(salon, "deviceSettings"))
        await click(window, find(ac, "fanSpeed_LOW"))
        assert ac.property("selectedFanSpeed") == "LOW"
        assert ac.property("width") <= width and ac.property("height") <= height
        screenshot(window, f"09-nawiew-{width}x{height}")
        await click(window, find(ac, "closeSettings"))
        await click(window, find(window, "upstairsTab"))
    await backend.shutdown()
    engine.clearComponentCache()
    errors = [w for w in warnings if "Populating font family aliases" not in w]
    assert not errors, errors
    print("UI checks passed: cards, popups, saves, switches, washer states, 3 display sizes; no QML warnings.")


with loop:
    loop.run_until_complete(run())
