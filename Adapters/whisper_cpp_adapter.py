"""Local, bounded STT worker; WAV travels over stdin, no recording files."""
import asyncio
import io
import os
from pathlib import Path
import sys
import time
import wave
from array import array
from dataclasses import dataclass


@dataclass(frozen=True)
class Transcription:
    text: str
    seconds: float


def wav_bytes(pcm, fmt):
    if not (8000 <= fmt.rate <= 96000 and 1 <= fmt.channels <= 4):
        raise ValueError("Invalid PCM format")
    if not pcm or len(pcm) > min(4 * 1024 * 1024, fmt.bytes_per_second * 5) or len(pcm) % fmt.frame_bytes:
        raise ValueError("Invalid PCM length")
    if sys.byteorder != "little":
        samples = array('h', pcm)
        samples.byteswap()
        pcm = samples.tobytes()
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(fmt.channels)
        wav.setsampwidth(2)
        wav.setframerate(fmt.rate)
        wav.writeframes(pcm)
    return output.getvalue()


class WhisperCppAdapter:
    def __init__(self, executable, model, *, spawn=None, timeout=60):
        self.executable, self.model = Path(executable).expanduser(), Path(model).expanduser()
        self._spawn = spawn or asyncio.create_subprocess_exec
        self._timeout = timeout

    def available(self):
        return self.executable.is_file() and os.access(self.executable, os.X_OK) and self.model.is_file()

    async def _terminate(self, process):
        if process.returncode is not None:
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

    async def transcribe(self, pcm, fmt):
        if not self.available():
            raise FileNotFoundError("Local speech runtime unavailable")
        audio = wav_bytes(pcm, fmt)
        # With stdin input, whisper.cpp disables its segment-print callback.
        # Explicit text output is required even when the process exits cleanly.
        args = [str(self.executable), '-m', str(self.model), '-l', 'pl', '-t', '2',
                '-ng', '-nt', '-np', '-otxt', '-of', '-', '-f', '-']
        if sys.platform.startswith('linux'):
            args = ['/usr/bin/nice', '-n', '10', *args]
        # In particular do not inherit device passwords, proxy settings or the
        # PyInstaller LD_LIBRARY_PATH into the external executable.
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'OMP_NUM_THREADS': '2'}
        started = time.monotonic()
        process, spawn, tasks = None, None, []
        try:
            async with asyncio.timeout(self._timeout):
                spawn = asyncio.create_task(self._spawn(*args, stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                    env=env, limit=8192))
                process = await asyncio.shield(spawn)
                async def feed():
                    try:
                        process.stdin.write(audio)
                        await process.stdin.drain()
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    finally:
                        process.stdin.close()
                async def read():
                    result = bytearray()
                    while chunk := await process.stdout.read(4096):
                        result.extend(chunk)
                        if len(result) > 16384:
                            raise ValueError("Speech output limit exceeded")
                    return bytes(result)
                tasks = [asyncio.create_task(feed()), asyncio.create_task(read()),
                         asyncio.create_task(process.wait())]
                _, output, code = await asyncio.gather(*tasks)
                if code:
                    raise RuntimeError("Local speech worker failed")
                text = ' '.join(output.decode('utf-8', errors='strict').split())
                if len(text) > 2000:
                    raise ValueError("Transcription too long")
                return Transcription(text, time.monotonic() - started)
        finally:
            # Even cancellation during spawn must reclaim the created process.
            if process is None and spawn is not None:
                try:
                    process = await spawn
                except Exception:
                    pass
            if process is not None:
                await self._terminate(process)
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
