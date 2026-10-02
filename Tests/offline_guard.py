"""Python-side tripwire for accidental I/O; not an OS security sandbox."""
import importlib.abc
import os
import socket
import sys


class OfflineViolation(RuntimeError):
    pass


class OfflineGuard(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.violations = []

    def reject(self, operation):
        # Do not log addresses, credentials or file contents.
        self.violations.append(operation)
        raise OfflineViolation(f"Offline test blocked: {operation}")

    def find_spec(self, fullname, path=None, target=None):
        if fullname in {"Compositions.compositions", "bleak"}:
            self.reject(f"import {fullname}; inject a fake transport instead")
        return None

    def audit(self, event, args):
        if event in {"socket.connect", "socket.bind", "socket.sendto",
                     "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}:
            self.reject(event)
        if event == "socket.__new__" and args[1] not in {socket.AF_UNIX}:
            # asyncio/qasync socketpairs use AF_UNIX and remain available.
            self.reject("network socket creation")
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            name = os.path.basename(os.fsdecode(args[0]))
            if name == ".env" or name.endswith(".token") or name == "token.json":
                self.reject("credential file access")
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}:
            self.reject("child process")

    def install(self):
        # urllib3 probes IPv6 by binding ::1 during import. No probe is needed
        # for fake transports; disable it before installing the strict guard.
        socket.has_ipv6 = False
        sys.meta_path.insert(0, self)
        sys.addaudithook(self.audit)
