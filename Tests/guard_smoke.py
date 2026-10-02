"""Verify offline tripwires before any application test; all I/O must be denied."""
import importlib
from pathlib import Path
import socket
import subprocess
import sys

from Tests.offline_guard import OfflineGuard, OfflineViolation

guard = OfflineGuard()
guard.install()

operations = [
    lambda: socket.socket(socket.AF_INET),
    lambda: socket.socket(socket.AF_INET6),
    lambda: socket.getaddrinfo("offline-test.invalid", 80),
    lambda: Path(".env").read_text(),
    lambda: importlib.import_module("Compositions.compositions"),
    lambda: importlib.import_module("bleak"),
    lambda: subprocess.run([sys.executable, "-c", "pass"], check=True),
]
for operation in operations:
    try:
        operation()
    except OfflineViolation:
        pass
    else:
        raise AssertionError("Offline guard allowed a forbidden operation")
assert len(guard.violations) == len(operations)
# Local wakeup sockets must remain usable by asyncio.
left, right = socket.socketpair()
try:
    left.send(b"ok")
    assert right.recv(2) == b"ok"
finally:
    left.close()
    right.close()
print("Offline guard: 7 forbidden operations blocked; local socketpair works")
