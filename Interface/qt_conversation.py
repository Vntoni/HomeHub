"""Hands-free half-duplex conversation. Only this controller owns its audio stream."""
import asyncio
import inspect
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from App.voice_activity import UtteranceBuffer, is_toggle


class ConversationController(QObject):
    changed = Signal()

    def __init__(self, factory=None, transcriber=None, speaker=None, answerer=None,
                 parent=None, preferences=None, cooldown=.7):
        super().__init__(parent)
        self.factory, self.transcriber, self.speaker, self.answerer = factory, transcriber, speaker, answerer
        self.preferences, self.cooldown = preferences, cooldown
        self._enabled = self._active = self._connected = self._closed = False
        self._state, self._message = 'off', 'Nasłuch hasła wyłączony.'
        self._question = self._answer = ''
        self._task = self._adapter = None
        self._input = self._output = ''
        self._retry = QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.timeout.connect(self._auto_start)
        self._retries = 0

    @Property(bool, notify=changed)
    def enabled(self): return self._enabled
    @Property(bool, notify=changed)
    def active(self): return self._active
    @Property(str, notify=changed)
    def state(self): return self._state
    @Property(str, notify=changed)
    def message(self): return self._message
    @Property(str, notify=changed)
    def question(self): return self._question
    @Property(str, notify=changed)
    def answer(self): return self._answer
    @Property(bool, notify=changed)
    def available(self):
        return bool(self.factory and self.transcriber and self.speaker and
                    self.transcriber.available() and self.speaker.available())

    def _set(self, state, message):
        self._state, self._message = state, message
        self.changed.emit()

    def _save(self, key, value):
        if self.preferences is not None:
            self.preferences.setValue(key, value)
            self.preferences.sync()

    def _saved(self, key, default):
        if self.preferences is None:
            return default
        return self.preferences.value(key, default, type=type(default))

    def set_connected(self, connected):
        self._connected = connected
        if not connected:
            self._stop(False)
            if self._task:
                self._task.add_done_callback(lambda _: self.start('', '')
                    if not self._closed and self._connected and self._saved('enabled', False) else None)
        elif self._saved('enabled', self.preferences is not None):
            self._retries = 5
            self._auto_start()
        self.changed.emit()

    def _auto_start(self):
        if self._closed or not self._connected:
            return
        self.start('', '')
        if not self._enabled and self._retries > 0:
            self._retries -= 1
            self._retry.start(2000)

    def _devices_changed(self):
        # Explicitly stop on hotplug; do not silently switch the speaker/microphone.
        self._stop(False)
        self._set('error', 'Urządzenia audio zmieniły się. Włącz nasłuch ponownie.')

    @Slot(str, str)
    def start(self, input_id='', output_id=''):
        if self._closed or self._enabled:
            return
        if self._task is not None and not self._task.done():
            self._set('off', 'Kończenie poprzedniej rozmowy. Spróbuj ponownie za chwilę.')
            return
        if not self._connected or not self.available:
            self._set('error', 'Podłącz ReSpeaker i zainstaluj lokalny silnik mowy oraz głos Piper.')
            return
        try:
            self._adapter = self.factory(self._devices_changed)
            inputs, outputs = self._adapter.devices()
            def select(devices, requested, key):
                wanted = requested or self._saved(key, '')
                if wanted:
                    if wanted not in {d['id'] for d in devices}:
                        raise ValueError('Saved audio device is unavailable')
                    return wanted
                preferred = [d for d in devices if 'respeaker' in d['label'].lower().replace(' ', '')]
                choices = preferred or [d for d in devices if d.get('default')] or devices
                if len(choices) != 1:
                    raise ValueError('Choose one audio device')
                return choices[0]['id']
            self._input = select(inputs, input_id, 'input')
            self._output = select(outputs, output_id, 'output')
            self._enabled, self._active = True, False
            self._save('input', self._input)
            self._save('output', self._output)
            self._save('enabled', True)
            self._question = self._answer = ''
            self._task = asyncio.create_task(self._run())
            self.changed.emit()
        except Exception:
            if self._adapter:
                self._adapter.close()
                self._adapter = None
            self._enabled = False
            self._set('error', 'Nie można rozpocząć nasłuchu. Wybierz mikrofon i głośnik w panelu.')

    def _reset_context(self):
        owner = getattr(self.answerer, '__self__', None)
        if hasattr(owner, 'reset'):
            owner.reset()

    async def _capture(self):
        future = asyncio.get_running_loop().create_future()
        segmenter = None
        def data(chunk):
            if segmenter is None or future.done():
                return
            try:
                result = segmenter.feed(chunk)
                if result is not None:
                    future.set_result(result)
            except Exception as exc:
                future.set_exception(exc)
        def error():
            if not future.done():
                future.set_exception(RuntimeError('Audio input failed'))
        adapter = self._adapter
        fmt = adapter.record(self._input, data, error)
        segmenter = UtteranceBuffer(fmt, threshold=self._saved('rmsThreshold', .008))
        try:
            pcm, too_long = await future
            return pcm, fmt, too_long
        finally:
            adapter.stop()

    async def _say(self, text):
        self._answer = text
        self._set('speaking', 'HomeHub mówi — mikrofon wstrzymany.')
        pcm, fmt = await self.speaker.synthesize(text)
        if not self._enabled:
            return
        future = asyncio.get_running_loop().create_future()
        def done():
            if not future.done(): future.set_result(None)
        def error():
            if not future.done(): future.set_exception(RuntimeError('Audio output failed'))
        adapter = self._adapter
        adapter.play(self._output, pcm, fmt, done, error)
        try:
            await asyncio.wait_for(future, len(pcm) / fmt.bytes_per_second + 5)
        finally:
            adapter.stop()
        await asyncio.sleep(self.cooldown)  # Do not feed the speaker's acoustic tail into STT.

    async def _run(self):
        self._reset_context()
        try:
            while self._enabled:
                self._set('listening' if self._active else 'waiting',
                          'Słucham pytania. „Gugu gaga” kończy rozmowę.' if self._active
                          else 'Nasłuch hasła „Gugu gaga” — lokalnie.')
                pcm, fmt, too_long = await self._capture()
                if too_long:
                    if self._active:
                        await self._say('Powiedz krótsze pytanie, do dwunastu sekund.')
                    continue
                self._set('processing', 'Rozpoznaję wypowiedź lokalnie…')
                transcript = await self.transcriber.transcribe(pcm, fmt)
                if not self._enabled:
                    break
                text = transcript.text.strip()
                if not text:
                    continue
                if is_toggle(text):
                    self._active = not self._active
                    self._reset_context()
                    self._question = ''
                    await self._say('Słucham.' if self._active else 'Kończę rozmowę. Czekam na hasło.')
                elif self._active:
                    self._question = text
                    self.changed.emit()
                    reply = self.answerer(text)
                    if inspect.isawaitable(reply):
                        reply = await reply
                    if not self._enabled:
                        break
                    await self._say(reply.answer or 'Nie rozumiem. Powtórz pytanie.')
                # Standby speech is discarded, never sent to the language model.
        except asyncio.CancelledError:
            raise
        except Exception:
            self._set('error', 'Rozmowa została zatrzymana po błędzie audio lub mowy. Włącz nasłuch ponownie.')
        finally:
            self._enabled = self._active = False
            if self._adapter:
                self._adapter.close()
                self._adapter = None
            if self.speaker:
                await self.speaker.aclose()
            self._reset_context()
            self.changed.emit()

    def _stop(self, persist):
        self._retry.stop()
        if persist:
            self._save('enabled', False)
        self._enabled = self._active = False
        if self._adapter:
            self._adapter.close()
            self._adapter = None
        if self._task and not self._task.done():
            self._task.cancel()
        self._question = self._answer = ''
        self._set('off', 'Nasłuch wyłączony. Mikrofon nie nagrywa.')

    @Slot()
    def stop(self):
        self._stop(True)

    def shutdown(self):
        self._closed = True
        self._stop(False)  # Preserve the user's restart preference.

    async def aclose(self):
        self.shutdown()
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)
        # Also handles stop before the session coroutine ever starts.
        if self._adapter:
            self._adapter.close()
            self._adapter = None
        if self.speaker:
            await self.speaker.aclose()
