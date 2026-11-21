import asyncio
import io
import struct
import wave
from unittest.mock import AsyncMock, Mock

import pytest
from Adapters.piper_tts import PiperTts, spoken_text
from Config.tts_runtime import MODEL


class Process:
    def __init__(self, output):
        self.output = bytearray(output)
        self.returncode = None
        self.stdin = Mock(drain=AsyncMock())
        self.stdout = Mock(readexactly=self.read)
        self.terminated = False

    async def read(self, count):
        result = bytes(self.output[:count])
        del self.output[:count]
        if len(result) != count:
            raise asyncio.IncompleteReadError(result, count)
        return result

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self): self.terminate()
    async def wait(self): return self.returncode


def wav():
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22050)
        output.writeframes(b'\0' * 4410)
    return stream.getvalue()


def runtime(tmp_path, output):
    for name in ['venv/bin/python', 'piper_worker.py', MODEL, MODEL + '.json', 'ready.json']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fake')
    process = Process(output)
    spawn = AsyncMock(return_value=process)
    return PiperTts(tmp_path, spawn), process, spawn


async def test_persistent_worker_pcm_and_isolated_environment(tmp_path):
    data = wav()
    speech, process, spawn = runtime(tmp_path, (struct.pack('!I', len(data)) + data) * 2)
    for _ in range(2):
        pcm, fmt = await speech.synthesize('21 °C')
        assert pcm == b'\0' * 4410 and fmt.rate == 22050
    spawn.assert_awaited_once()
    assert set(spawn.call_args.kwargs['env']) == {'PATH', 'LANG', 'OMP_NUM_THREADS'}
    await speech.aclose()
    assert process.terminated


@pytest.mark.parametrize('output', [struct.pack('!I', 99999999), struct.pack('!I', 100)+b'bad',
                                     struct.pack('!I', 44)+b'X'*44])
async def test_bad_audio_terminates_worker(tmp_path, output):
    speech, process, spawn = runtime(tmp_path, output)
    with pytest.raises((ValueError, asyncio.IncompleteReadError, wave.Error)):
        await speech.synthesize('Słucham.')
    assert process.terminated and speech.process is None


async def test_cancel_during_response_terminates_worker(tmp_path):
    speech, process, spawn = runtime(tmp_path, b'')
    started = asyncio.Event()
    async def read(count):
        started.set()
        await asyncio.Event().wait()
    process.stdout.readexactly = read
    task = asyncio.create_task(speech.synthesize('Słucham.'))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert process.terminated


def test_spoken_units_and_bound():
    assert 'stopni Celsjusza' in spoken_text('20 °C')
    assert 'procent' in spoken_text('60 %')
    assert len(spoken_text('a' * 900)) == 400
