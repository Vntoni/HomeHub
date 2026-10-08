import asyncio
import io
import wave
from unittest.mock import AsyncMock, Mock

import pytest
from PySide6.QtCore import QCoreApplication

from Adapters.whisper_cpp_adapter import WhisperCppAdapter, Transcription, wav_bytes
from Interface.qt_audio_probe import AudioProbeController
from Ports.audio_probe import PcmFormat
from Tests.fake_audio_probe import FakeAudioProbe


def test_wav_preserves_rate_channels_and_pcm_without_file():
    data = b'\x01\x00\x02\x00' * 100
    with wave.open(io.BytesIO(wav_bytes(data, PcmFormat(48000, 2)))) as wav:
        assert wav.getframerate() == 48000 and wav.getnchannels() == 2
        assert wav.readframes(100) == data


@pytest.mark.parametrize('data,fmt', [(b'', PcmFormat(16000, 1)), (b'\0', PcmFormat(16000, 1)),
    (b'\0\0', PcmFormat(1, 1)), (b'\0' * 160002, PcmFormat(16000, 1))])
def test_reject_invalid_or_oversized_audio(data, fmt):
    with pytest.raises(ValueError): wav_bytes(data, fmt)


class Process:
    def __init__(self, output=b'Jaka temperatura w lazience?', code=0, hanging=False):
        self.returncode = None
        self.code, self.output, self.hanging = code, output, hanging
        self.finished = asyncio.Event()
        self.stdin = Mock(drain=AsyncMock())
        self.stdout = Mock(read=self.read)
        self.terminated = False

    async def read(self, count):
        if self.hanging:
            await self.finished.wait()
        result, self.output = self.output[:count], self.output[count:]
        return result

    async def wait(self):
        if self.hanging:
            await self.finished.wait()
        self.returncode = self.code
        return self.code

    def terminate(self):
        self.terminated = True
        self.code = -15
        self.finished.set()

    def kill(self):
        self.terminate()


@pytest.fixture
def worker(tmp_path):
    exe = tmp_path / 'whisper-cli'
    exe.write_text('fake, never executed')
    exe.chmod(0o700)
    model = tmp_path / 'model.bin'
    model.write_bytes(b'fake')
    def create(process, **kwargs):
        spawn = AsyncMock(return_value=process)
        return WhisperCppAdapter(exe, model, spawn=spawn, **kwargs), spawn
    return create


async def test_worker_uses_stdin_polish_bounded_threads_and_clean_env(worker, monkeypatch):
    monkeypatch.setenv('ARISTON_PWD', 'secret')
    p = Process('Zażółć gęślą jaźń'.encode())
    adapter, spawn = worker(p)
    result = await adapter.transcribe(b'\0\x40' * 100, PcmFormat(16000, 1))
    assert result.text == 'Zażółć gęślą jaźń' and result.seconds >= 0
    args, kwargs = spawn.call_args
    assert args[args.index('-l') + 1] == 'pl'
    assert args[args.index('-t') + 1] == '2'
    assert args[-2:] == ('-f', '-')
    assert 'ARISTON_PWD' not in kwargs['env'] and 'LD_LIBRARY_PATH' not in kwargs['env']
    assert p.stdin.write.call_args.args[0].startswith(b'RIFF')
    p.stdin.close.assert_called_once()


async def test_stdin_inference_explicitly_emits_text_to_stdout(worker):
    # whisper.cpp 1.9.4 derives its output name from input '-'. That disables
    # the segment callback; without -otxt it exits 0 but returns no text.
    adapter, _ = worker(Process())
    async def cli(*args, **kwargs):
        output_name = args[args.index('-of') + 1] if '-of' in args else args[args.index('-f') + 1]
        emits_text = output_name == '-' and '-otxt' in args
        return Process(output='Jaka jest temperatura?'.encode() if emits_text else b'')
    adapter._spawn = cli
    result = await adapter.transcribe(b'\0\x40' * 100, PcmFormat(16000, 1))
    assert result.text == 'Jaka jest temperatura?'


async def test_deployment_smoke_rejects_successful_but_empty_transcription(monkeypatch, tmp_path):
    from Tools import voice_runtime_smoke as smoke
    worker = Mock(transcribe=AsyncMock(return_value=Transcription('', .1)))
    monkeypatch.setattr(smoke, 'WhisperCppAdapter', Mock(return_value=worker))
    with pytest.raises(RuntimeError, match='no usable transcript'):
        await smoke.main(tmp_path)
    pcm, fmt = worker.transcribe.call_args.args
    assert fmt == PcmFormat(48000, 2)
    assert len(pcm) == fmt.bytes_per_second * 5 and any(pcm)


@pytest.mark.parametrize('mode', ['timeout', 'cancel', 'overflow', 'error'])
async def test_worker_failure_and_cancellation_reap_process(worker, mode):
    process = Process(output=b'x' * 20000 if mode == 'overflow' else b'',
                      code=1 if mode == 'error' else 0, hanging=mode in ('timeout', 'cancel'))
    adapter, spawn = worker(process, timeout=.03 if mode == 'timeout' else 2)
    task = asyncio.create_task(adapter.transcribe(b'\0\x40' * 100, PcmFormat(16000, 1)))
    if mode == 'cancel':
        await asyncio.sleep(.01)
        task.cancel()
    with pytest.raises((TimeoutError, asyncio.CancelledError, ValueError, RuntimeError)):
        await task
    assert process.returncode is not None
    if mode in ('timeout', 'cancel'):
        assert process.terminated


async def test_cancel_during_spawn_still_reaps_child(worker):
    process = Process(hanging=True)
    adapter, _ = worker(process)
    entered, release = asyncio.Event(), asyncio.Event()
    async def spawn(*args, **kwargs):
        entered.set()
        await release.wait()
        return process
    adapter._spawn = spawn
    task = asyncio.create_task(adapter.transcribe(b'\0\x40' * 100, PcmFormat(16000, 1)))
    await entered.wait()
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError): await task
    assert process.terminated and process.returncode is not None


async def test_missing_runtime_does_not_spawn(tmp_path):
    spawn = AsyncMock()
    adapter = WhisperCppAdapter(tmp_path / 'missing', tmp_path / 'model', spawn=spawn)
    with pytest.raises(FileNotFoundError):
        await adapter.transcribe(b'\0\0', PcmFormat(16000, 1))
    spawn.assert_not_called()


@pytest.fixture
def controller():
    app = QCoreApplication.instance() or QCoreApplication([])
    audio = FakeAudioProbe()
    stt = Mock(available=Mock(return_value=True), transcribe=AsyncMock(return_value=Transcription('Włącz klimatyzację', .2)))
    p = AudioProbeController(lambda cb: audio, transcriber=stt)
    p.set_connected(True)
    p.openPanel()
    p.record('mic')
    audio.data(b'\0\x40' * 100)
    p.stop()
    yield p, audio, stt
    p.shutdown()


async def test_transcript_is_only_text_and_no_auto_inference(controller):
    p, audio, stt = controller
    stt.transcribe.assert_not_called()
    p.transcribe()
    p.transcribe()
    await p._stt_task
    assert p.transcript == 'Włącz klimatyzację' and p.state == 'idle'
    stt.transcribe.assert_awaited_once()
    assert audio.records == 1 and audio.plays == 0
    p.clear()
    assert not p.transcript


async def test_closing_cancels_and_waits_without_second_cancel(controller):
    p, audio, stt = controller
    entered, cleanup, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async def slow(*args):
        entered.set()
        try:
            await asyncio.Future()
        finally:
            cleanup.set()
            await release.wait()
    stt.transcribe.side_effect = slow
    p.transcribe()
    await entered.wait()
    p.closePanel()
    await cleanup.wait()
    close = asyncio.create_task(p.aclose())
    await asyncio.sleep(.01)
    assert not close.done() and not p.transcript
    release.set()
    await close
    assert p._stt_task.cancelled() and audio.closed


async def test_error_keeps_sample_for_retry_and_silence_does_not_infer(controller):
    p, audio, stt = controller
    stt.transcribe.side_effect = TimeoutError()
    p.transcribe()
    await p._stt_task
    assert p.state == 'error' and p.hasRecording and not p.transcript
    stt.transcribe.reset_mock()
    p._peak = 0
    p.transcribe()
    stt.transcribe.assert_not_called()
