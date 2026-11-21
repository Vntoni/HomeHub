"""Bounded persistent Piper worker, isolated from PyInstaller and device credentials."""
import asyncio
import io
import json
import struct
import sys
import wave
from array import array

from Config.tts_runtime import MODEL, runtime_dir
from Ports.audio_probe import PcmFormat


def spoken_text(text):
    return text.replace('°C', ' stopni Celsjusza').replace('%', ' procent').replace('—', ',')[:400]


class PiperTts:
    def __init__(self, root=None, spawn=None):
        self.root = root or runtime_dir()
        self.spawn = spawn or asyncio.create_subprocess_exec
        self.process = None
        self.lock = asyncio.Lock()

    def available(self):
        return all((self.root / path).is_file() for path in
                   ('venv/bin/python', 'piper_worker.py', MODEL, MODEL + '.json', 'ready.json'))

    async def aclose(self):
        process, self.process = self.process, None
        if process is None or process.returncode is not None:
            return
        try:
            process.terminate()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(process.wait(), 2)
        except TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()

    async def synthesize(self, text):
        text = spoken_text(text)
        if not text.strip() or not self.available():
            raise ValueError('Speech runtime/text unavailable')
        async with self.lock:
            pending = None
            try:
                async with asyncio.timeout(40):
                    if self.process is None or self.process.returncode is not None:
                        pending = asyncio.create_task(self.spawn(
                            str(self.root / 'venv/bin/python'), str(self.root / 'piper_worker.py'),
                            str(self.root / MODEL), stdin=asyncio.subprocess.PIPE,
                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'OMP_NUM_THREADS': '2'},
                            limit=65536))
                        self.process = await asyncio.shield(pending)
                    self.process.stdin.write((json.dumps(text) + '\n').encode())
                    await self.process.stdin.drain()
                    length = struct.unpack('!I', await self.process.stdout.readexactly(4))[0]
                    if not 44 <= length <= 3 * 1024 * 1024:
                        raise ValueError('Invalid speech audio length')
                    data = await self.process.stdout.readexactly(length)
                    with wave.open(io.BytesIO(data)) as wav:
                        fmt = PcmFormat(wav.getframerate(), wav.getnchannels())
                        if wav.getsampwidth() != 2 or fmt.channels != 1 or not 8000 <= fmt.rate <= 48000:
                            raise ValueError('Invalid speech format')
                        if wav.getnframes() > fmt.rate * 40:
                            raise ValueError('Speech exceeds 40 seconds')
                        pcm = wav.readframes(wav.getnframes())
                        if len(pcm) != wav.getnframes() * fmt.frame_bytes:
                            raise ValueError('Truncated speech audio')
                    if sys.byteorder != 'little':
                        samples = array('h', pcm)
                        samples.byteswap()
                        pcm = samples.tobytes()
                    return pcm, fmt
            except BaseException:
                if pending is not None and self.process is None:
                    try:
                        self.process = await pending
                    except Exception:
                        pass
                await self.aclose()
                raise
