"""Read Linux USB descriptors without opening the device or recording audio."""
from pathlib import Path

from Ports.respeaker import RespeakerStatus


class RespeakerUsbAdapter:
    # Published by the manufacturer in reSpeaker_Lite/xmos_firmwares/dfu_guide.md.
    # This identifies the USB device, not its firmware mode or audio readiness.
    USB_ID = ("2886", "0019")

    def __init__(self, devices_path=Path("/sys/bus/usb/devices")):
        self._devices_path = Path(devices_path)

    def read_status(self) -> RespeakerStatus:
        try:
            devices = list(self._devices_path.iterdir())
        except FileNotFoundError:
            return RespeakerStatus(False, "Wykrywanie ReSpeaker wymaga USB sysfs w Linuxie")
        unreadable = False
        for device in devices:
            try:
                vendor = (device / "idVendor").read_text(encoding="ascii").strip().lower()
                if vendor != self.USB_ID[0]:
                    continue
                product = (device / "idProduct").read_text(encoding="ascii").strip().lower()
                if (vendor, product) == self.USB_ID:
                    return RespeakerStatus(True, "ReSpeaker podłączony przez USB — nagrywanie wyłączone")
            except (FileNotFoundError, NotADirectoryError):
                # Interfaces have no idVendor; unplug may race any file read.
                continue
            except (OSError, UnicodeError):
                unreadable = True
        if unreadable:
            return RespeakerStatus(False, "Nie można potwierdzić połączenia ReSpeaker — błąd odczytu USB")
        return RespeakerStatus()
