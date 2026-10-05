"""Offline Qt interaction and layout check. Optional screenshot directory argument.

QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python Tests/ui_smoke.py /tmp/homehub-ui
"""
import asyncio
from pathlib import Path
import socket
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QObject, QPointF, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from qasync import QEventLoop
from Compositions.demo import build_demo_backend
from App.operations import run_blocking
from App.respeaker_service import RespeakerService
from Ports.respeaker import RespeakerStatus
from Tests.fake_audio_probe import FakeAudioProbe
from Adapters.whisper_cpp_adapter import Transcription
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
output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "test-results" / "ui"
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
    # qasync slots may finish after the rendering delay on a loaded CI host.
    async with asyncio.timeout(3):
        while not item.property("enabled"):
            await asyncio.sleep(0.01)
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
    if item.objectName() == "applySettings":
        async with asyncio.timeout(3):
            while any(find(window, name).property("saving")
                      for name in ("acPopup", "boilerPopup", "heaterPopup")):
                await asyncio.sleep(0.01)


def screenshot(window, name):
    if output:
        assert window.grabWindow().save(str(output / (name + ".png")))


async def run():
    backend = await build_demo_backend()
    class UsbProbe:
        state = RespeakerStatus()
        def read_status(self):
            return self.state
    usb = UsbProbe()
    backend._respeaker = RespeakerService(usb, .02)
    audio = FakeAudioProbe()
    backend.audioProbe._factory = lambda changed: audio
    class FakeSTT:
        def available(self): return True
        async def transcribe(self, pcm, fmt):
            await asyncio.sleep(.05)
            return Transcription("Jaka jest temperatura w łazience?", .05)
    backend.audioProbe._transcriber = FakeSTT()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("demoMode", True)
    engine.addImportPath(str(Path(__file__).resolve().parents[1] / "View"))
    engine.loadFromModule("Example", "main")
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    await backend.init_all()
    await asyncio.sleep(0.4)
    assert window.property("isReady")
    microphone = find(window, "microphoneStatus")
    microphone_icon = find(window, "microphoneIcon")
    def icon_ready():
        # QQuickImageBase's enum is not registered with PySide; evaluate it in
        # JS. Ready is 1; the ad-hoc expression has no QtQuick import namespace.
        expression = QQmlExpression(engine.rootContext(), microphone_icon, "status === 1")
        value = expression.evaluate()
        assert not expression.hasError(), expression.error().toString()
        return value[0] if isinstance(value, tuple) else value
    assert not microphone.property("connected")
    assert str(microphone_icon.property("source").toString()).endswith("microphone-disconnected.svg")
    assert icon_ready()  # SVG packaged and loaded.
    screenshot(window, "00-microphone-disconnected")
    usb.state = RespeakerStatus(True, "ReSpeaker podłączony przez USB — nagrywanie wyłączone")
    async with asyncio.timeout(2):
        while not microphone.property("connected"):
            await asyncio.sleep(.01)
    assert microphone.property("statusText") == usb.state.message
    assert microphone_icon.property("source").toString().endswith("microphone-connected.svg")
    await asyncio.sleep(.05)
    assert icon_ready()
    screenshot(window, "00-microphone-connected")
    for width, height in [(1280, 720), (800, 480)]:
        window.setWidth(width)
        window.setHeight(height)
        await asyncio.sleep(.1)
        await click(window, microphone)
        popup = find(window, "audioProbePopup")
        assert popup.property("opened") and not backend.audioProbe.busy
        assert not find(popup, "recordAudioProbe").property("enabled")
        find(popup, "audioInputSelector").setProperty("currentIndex", 0)
        find(popup, "audioOutputSelector").setProperty("currentIndex", 0)
        await click(window, find(popup, "recordAudioProbe"))
        audio.data(b'\x00\x40' * 1600)
        assert backend.audioProbe.state == "recording" and microphone.property("active")
        assert not find(popup, "playAudioProbe").property("enabled")
        assert find(popup, "audioLevel").property("value") == .5
        screenshot(window, f"00-audio-record-{width}x{height}")
        # Exercise the real Qt deadline, not only the explicit stop action.
        async with asyncio.timeout(6):
            while backend.audioProbe.busy:
                await asyncio.sleep(.05)
        assert backend.audioProbe.hasRecording
        await click(window, find(popup, "playAudioProbe"))
        assert backend.audioProbe.state == "playing" and audio.played == b'\x00\x40' * 1600
        audio.done()
        await click(window, find(popup, "transcribeAudioProbe"))
        async with asyncio.timeout(2):
            while backend.audioProbe.busy:
                await asyncio.sleep(.01)
        assert find(popup, "transcriptionText").property("text") == "Jaka jest temperatura w łazience?"
        screenshot(window, f"00-transcription-{width}x{height}")
        screenshot(window, f"00-audio-ready-{width}x{height}")
        await click(window, find(popup, "recordAudioProbe"))
        await click(window, find(popup, "closeAudioProbe"))
        assert not backend.audioProbe.busy and not backend.audioProbe.hasRecording
        assert not backend.audioProbe.transcript
    window.setWidth(1200)
    window.setHeight(800)
    usb.state = RespeakerStatus()
    async with asyncio.timeout(2):
        while microphone.property("connected"):
            await asyncio.sleep(.01)
    assert microphone_icon.property("source").toString().endswith("microphone-disconnected.svg")
    refresh_timer = find(window, "deviceRefreshTimer")
    assert refresh_timer.property("interval") == 900000
    # Exercise the actual timer with a shortened test interval. A slow cloud
    # read and a simultaneous manual refresh must share one cycle, without writes.
    entered, release = asyncio.Event(), asyncio.Event()
    reads, writes = [], []
    original_read = backend._climate.refresh
    async def slow_read(room):
        reads.append(room)
        if room == "Salon":
            entered.set()
            await release.wait()
        backend._climate.units[room]["current"] = 21.75
    saved_writes = []
    for service in (backend._climate, backend._boiler, backend._heater):
        for name in dir(service):
            if name.startswith(("set_", "turn_on", "turn_off")):
                original_method = getattr(service, name)
                saved_writes.append((service, name, original_method))
                async def forbidden_write(*args, name=name):
                    writes.append(name)
                    raise AssertionError("Refresh sent a command")
                setattr(service, name, forbidden_write)
    backend._climate.refresh = slow_read
    try:
        window.setProperty("deviceRefreshIntervalMs", 40)
        await asyncio.wait_for(entered.wait(), 2)
        manual = backend.refresh_connection()
        await asyncio.sleep(.15)
        assert reads == ["Salon"]
        window.setProperty("deviceRefreshIntervalMs", 900000)
        release.set()
        await asyncio.wait_for(manual, 2)
        await asyncio.sleep(.05)
        assert reads == ["Salon", "Jadalnia"]
        assert not window.property("refreshing")
        assert find(window, "card_Salon").property("currentTemperature") == 21.75
        assert writes == []
    finally:
        release.set()
        window.setProperty("deviceRefreshIntervalMs", 900000)
        backend._climate.refresh = original_read
        for service, name, original_method in saved_writes:
            setattr(service, name, original_method)
    screenshot(window, "00-start")
    salon = find(window, "card_Salon")
    # Failure preserves the last displayed boiler values and marks them stale.
    boiler_card = find(window, "card_boiler")
    before = boiler_card.property("currentTemperature")
    original_refresh = backend._boiler.refresh
    async def failed_refresh():
        raise ConnectionError("offline test")
    backend._boiler.refresh = failed_refresh
    await backend.refresh_connection()
    await asyncio.sleep(.05)
    assert boiler_card.property("stale")
    assert boiler_card.property("currentTemperature") == before
    backend._boiler.refresh = original_refresh
    await backend.refresh_connection()
    await asyncio.sleep(.05)
    assert not boiler_card.property("stale")
    assert salon.property("targetTemperature") == 22.0
    screenshot(window, "01-parter")
    await click(window, find(window, "openMap"))
    temperature_map = find(window, "temperatureMap")
    assert temperature_map.property("opened")
    def map_value(expression):
        evaluator = QQmlExpression(engine.rootContext(), temperature_map, expression)
        result = evaluator.evaluate()
        assert not evaluator.hasError(), evaluator.error().toString()
        return result[0] if isinstance(result, tuple) else result
    await asyncio.to_thread(backend.sensorTempChanged.emit, "salon", None)
    await asyncio.to_thread(backend.sensorHumidityChanged.emit, "jadalnia", None)
    await asyncio.sleep(0.05)
    assert map_value("tempText(tempSalon)") == "brak danych"
    assert map_value("humText(humJadalnia)") == "brak danych"
    assert map_value("roomColor(tempSalon)") == "#2a2a2a"
    backend.sensorTempChanged.emit("salon", 0.0)
    backend.sensorHumidityChanged.emit("jadalnia", 0.0)
    await asyncio.sleep(0.05)
    assert map_value("tempText(tempSalon)") == "0,0°C"
    assert map_value("humText(humJadalnia)") == "0,0%"
    backend.sensorTempChanged.emit("salon", 21.5)
    backend.sensorTempChanged.emit("jadalnia", 20.0)
    await asyncio.sleep(0.05)
    assert map_value("tempText(tempSalon)") == "21,5°C"
    assert map_value("tempText(tempJadalnia)") == "20,0°C"
    backend.sensorTempChanged.emit("lazienka", 20.6)
    backend.sensorHumidityChanged.emit("lazienka", 65.0)
    await asyncio.sleep(.05)
    assert map_value("tempText(tempWC)") == "20,6°C"
    assert map_value("humText(humWC)") == "65,0%"
    await click(window, find(temperature_map, "closeMap"))

    await click(window, find(salon, "deviceSettings"))
    ac = find(window, "acPopup")
    assert ac.property("opened") and ac.property("loaded"), warnings
    assert ac.property("selectedFanSpeed") == "AUTO"
    airflow = find(ac, "airflowSelector")
    assert airflow.property("count") == 5
    airflow.setProperty("currentIndex", 4)
    airflow.activated.emit(4)
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
    assert backend._climate.airflow("Salon") == "SWING"
    assert ac.property("currentAirflow") == "SWING"
    assert ac.property("currentFanSpeed") == "QUIET"
    assert not ac.property("saving") and not ac.property("failed")
    assert salon.property("targetTemperature") == 22.5
    screenshot(window, "03-wynik-zapisu")
    await click(window, find(ac, "closeSettings"))
    # Settings for an already-off AC are read-only. Turning it on remains
    # available through the dedicated power switch.
    backend._climate.units["Jadalnia"]["mode"] = "OFF"
    backend._climate.units["Jadalnia"]["power"] = False
    await backend.publish_dashboard()
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
    # Opening includes an animation and asynchronous readback. Do not assert
    # the result after only the click helper's fixed rendering delay.
    async with asyncio.timeout(3):
        while not (ac.property("opened") and ac.property("loaded")
                   and ac.property("room") == "Jadalnia"):
            await asyncio.sleep(.01)
    assert ac.property("loadedMode") == "OFF"
    assert not find(ac, "applySettings").property("enabled")
    await click(window, find(ac, "acMode_HEAT"))
    assert not find(ac, "applySettings").property("enabled")
    assert find(ac, "acSettingsBlockedReason").property("visible")
    # Fresh state changes update the guard without overwriting the form draft.
    backend.modeReceived.emit("Jadalnia", "HEAT")
    assert find(ac, "applySettings").property("enabled")
    backend.modeReceived.emit("Jadalnia", "OFF")
    assert not find(ac, "applySettings").property("enabled")
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
    # A timed-out blocking command keeps both the form and shared-client cards
    # disabled until the real worker ends. It must not send the next setting.
    release = threading.Event()
    def blocked_transport():
        assert release.wait(3)
    async def delayed_mode(*args):
        await run_blocking(blocked_transport)
    backend._heater.set_mode = delayed_mode
    backend._command_timeout = .05
    target_before = backend._heater.get_target_temp("Julia")
    try:
        await click(window, find(heater, "temperaturePlus"))
        await click(window, find(heater, "applySettings"))
        assert heater.property("failed") and not heater.property("saving")
        assert heater.property("transportBusy")
        assert not find(heater, "applySettings").property("enabled")
        assert not find(julia, "devicePower").property("enabled")
        assert find(window, "card_Juras").property("transportBusy")
        release.set()
        async with asyncio.timeout(2):
            while heater.property("transportBusy"):
                await asyncio.sleep(.01)
        assert backend._heater.get_target_temp("Julia") == target_before
    finally:
        release.set()
        backend._heater.set_mode = original
        backend._command_timeout = 45
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
