"""USB descriptors are synthetic files; no real USB or audio is opened."""
import asyncio
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest

from Adapters.respeaker_usb_adapter import RespeakerUsbAdapter
from App.respeaker_service import RespeakerService
from Compositions.demo import build_demo_backend
from Ports.respeaker import RespeakerStatus


def usb_device(root, name="1-2", vendor="2886", product="0019"):
    path = root / name
    path.mkdir()
    (path / "idVendor").write_text(vendor + "\n")
    (path / "idProduct").write_text(product + "\n")
    return path


def test_empty_usb_and_missing_sysfs_do_not_require_addon(tmp_path):
    assert RespeakerUsbAdapter(tmp_path).read_status() == RespeakerStatus()
    missing = RespeakerUsbAdapter(tmp_path / "absent").read_status()
    assert not missing.connected
    assert "Linux" in missing.message


@pytest.mark.parametrize("vendor,product", [("2886", "0018"), ("1234", "0019"), ("0000", "0000")])
def test_other_usb_devices_are_not_respeaker_lite(tmp_path, vendor, product):
    usb_device(tmp_path, vendor=vendor, product=product)
    assert not RespeakerUsbAdapter(tmp_path).read_status().connected


def test_detect_disconnect_and_reconnect_on_another_usb_port(tmp_path):
    path = usb_device(tmp_path)
    (tmp_path / "1-2:1.0").mkdir()  # USB interface, no vendor descriptor.
    adapter = RespeakerUsbAdapter(tmp_path)
    assert adapter.read_status().connected
    (path / "idProduct").unlink()  # unplug racing enumeration
    assert not adapter.read_status().connected
    usb_device(tmp_path, name="1-3")
    assert adapter.read_status().connected


def test_unreadable_descriptor_is_not_reported_as_connected(tmp_path, monkeypatch):
    path = usb_device(tmp_path)
    original = Path.read_text
    def read(file, *args, **kwargs):
        if file == path / "idVendor":
            raise PermissionError("private path")
        return original(file, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    state = RespeakerUsbAdapter(tmp_path).read_status()
    assert not state.connected and "błąd" in state.message
    assert "private" not in state.message


@pytest.mark.parametrize("interval", [0, -1, float("inf"), float("nan")])
def test_poll_interval_must_be_bounded(interval):
    with pytest.raises(ValueError):
        RespeakerService(Mock(), interval)


async def test_monitor_runs_off_ui_thread_and_only_publishes_changes():
    owner = threading.get_ident()
    calls, states = [], []
    sequence = [False, False, True, True, False]
    finished = asyncio.Event()
    def read():
        calls.append(threading.get_ident())
        connected = sequence[min(len(calls) - 1, len(sequence) - 1)]
        return RespeakerStatus(connected, "connected" if connected else "disconnected")
    def update(state):
        assert threading.get_ident() == owner
        states.append(state.connected)
        if states == [False, True, False]:
            finished.set()
    service = RespeakerService(Mock(read_status=read), .005)
    task = asyncio.create_task(service.run(update))
    try:
        await asyncio.wait_for(finished.wait(), 2)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert states == [False, True, False]
    assert all(thread != owner for thread in calls)


async def test_probe_error_recovers_without_restarting_app(caplog):
    recovered = asyncio.Event()
    statuses = []
    def update(status):
        statuses.append(status)
        if status.connected:
            recovered.set()
    probe = Mock(read_status=Mock(side_effect=[PermissionError("secret path"), RespeakerStatus(True, "OK")]))
    task = asyncio.create_task(RespeakerService(probe, .005).run(update))
    try:
        await asyncio.wait_for(recovered.wait(), 2)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not statuses[0].connected and statuses[1].connected
    assert "PermissionError" in caplog.text and "secret path" not in caplog.text


async def test_backend_monitor_is_optional_single_and_stopped_on_shutdown():
    backend = await build_demo_backend()
    assert not backend.respeakerConnected
    backend._start_respeaker_monitor()
    assert backend._respeaker_task is None
    backend._respeaker = RespeakerService(Mock(read_status=Mock(return_value=RespeakerStatus(True, "USB"))), .005)
    updated = asyncio.Event()
    backend.respeakerStatusChanged.connect(updated.set)
    await backend.init_all()
    task = backend._respeaker_task
    backend._start_respeaker_monitor()
    assert backend._respeaker_task is task
    await asyncio.wait_for(updated.wait(), 2)
    assert backend.respeakerConnected and backend.respeakerStatusText == "USB"
    await backend.shutdown()
    assert task.done() and task.cancelled()
    backend._on_respeaker_status(RespeakerStatus())
    assert backend.respeakerConnected  # No late notifications during shutdown.
    assert not backend._lifecycle_tasks


async def test_shutdown_during_probe_waits_for_read_worker():
    entered, release = threading.Event(), threading.Event()
    def read():
        entered.set()
        assert release.wait(2)
        return RespeakerStatus(True, "USB")
    backend = await build_demo_backend()
    backend._respeaker = RespeakerService(Mock(read_status=read), .005)
    backend._start_respeaker_monitor()
    assert await asyncio.to_thread(entered.wait, 1)
    shutdown = asyncio.create_task(backend.shutdown())
    try:
        await asyncio.sleep(.02)
        assert not shutdown.done()
        assert not backend.respeakerConnected
    finally:
        release.set()
        await asyncio.wait_for(shutdown, 2)
    assert not backend.respeakerConnected
    assert backend._respeaker_task.cancelled()
