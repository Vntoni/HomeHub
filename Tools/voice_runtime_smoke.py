"""Standalone real-process check on Pi: synthetic silence, no microphone/config."""
import asyncio
from pathlib import Path
import resource
import sys
from PySide6.QtCore import QCoreApplication
from qasync import QEventLoop

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Adapters.whisper_cpp_adapter import WhisperCppAdapter
from Config.voice_runtime import runtime_dir
from Ports.audio_probe import PcmFormat


async def main():
    root = runtime_dir()
    worker = WhisperCppAdapter(root / 'whisper-cli', root / 'ggml-tiny.bin')
    # Exercise stereo 48 kHz conversion used by many Qt capture devices.
    result = await worker.transcribe(b'\0' * 48000 * 2 * 2 * 5, PcmFormat(48000, 2))
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    print(f"Synthetic STT smoke OK: seconds={result.seconds:.2f}; child_maxrss_KiB={usage.ru_maxrss}; "
          "no microphone used; Polish accuracy not measured")


if __name__ == '__main__':
    app = QCoreApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_until_complete(main())
