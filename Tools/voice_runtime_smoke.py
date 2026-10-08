"""Real-process checks: public speech fixture and silence, no microphone/config."""
import argparse
import asyncio
from array import array
from pathlib import Path
import resource
import sys
import wave
from PySide6.QtCore import QCoreApplication
from qasync import QEventLoop

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Adapters.whisper_cpp_adapter import WhisperCppAdapter
from Config.voice_runtime import runtime_dir
from Ports.audio_probe import PcmFormat


def speech_fixture():
    path = Path(__file__).resolve().parents[1] / 'Tests/fixtures/audio/jfk-5s.wav'
    with wave.open(str(path), 'rb') as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()) != (16000, 1, 2, 80000):
            raise ValueError('Unexpected speech fixture format')
        samples = array('h', wav.readframes(80000))
    if sys.byteorder != 'little':
        samples.byteswap()
    # Repeat each sample at 48 kHz in both channels to exercise Qt-style input.
    return array('h', (sample for sample in samples for _ in range(6))).tobytes()


async def main(root):
    worker = WhisperCppAdapter(root / 'whisper-cli', root / 'ggml-tiny.bin')
    speech = await worker.transcribe(speech_fixture(), PcmFormat(48000, 2))
    if len(speech.text.split()) < 3:
        raise RuntimeError('Speech fixture returned no usable transcript; refusing deployment')
    print(f"Speech STT smoke OK: seconds={speech.seconds:.2f}; nonempty transcript verified; "
          "public fixture; no microphone used; Polish accuracy not measured", flush=True)
    # Exercise stereo 48 kHz conversion used by many Qt capture devices.
    result = await worker.transcribe(b'\0' * 48000 * 2 * 2 * 5, PcmFormat(48000, 2))
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    rss_kib = usage.ru_maxrss // 1024 if sys.platform == 'darwin' else usage.ru_maxrss
    print(f"Synthetic STT smoke OK: seconds={result.seconds:.2f}; child_maxrss_KiB={rss_kib}; "
          "no microphone used; Polish accuracy not measured")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-dir', type=Path, default=runtime_dir())
    args = parser.parse_args()
    app = QCoreApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_until_complete(main(args.runtime_dir))
