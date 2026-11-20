"""Small read-only agent. Cache values and response wording stay outside the LLM."""
import time

from App.voice_queries import Reply, parse_question


class LocalHomeAgent:
    def __init__(self, cache, client, clock=time.monotonic):
        self.cache, self.client, self.clock = cache, client, clock
        self.reset()

    def reset(self):
        self.previous = None
        self.expires = 0
        self.generation = getattr(self, 'generation', 0) + 1

    async def answer(self, text):
        generation = self.generation
        if not isinstance(text, str) or not text.strip() or len(text) > 300:
            return Reply('', 'Zadaj krótkie pytanie o dom.')
        parsed = parse_question(text)
        if parsed:
            kind, room, _ = parsed
            intent = {'kind': kind, 'room': room}
        else:
            try:
                intent = await self.client.classify(
                    text, self.previous if self.clock() < self.expires else None)
            except Exception:
                self.reset()
                return Reply('', 'Lokalny model jest niedostępny lub nie zwrócił poprawnej odpowiedzi. '
                             'Spróbuj ponownie albo zapytaj np. „Temperatura w łazience”.')
        if generation != self.generation:
            return Reply('', '')
        kind, room = intent['kind'], intent['room']
        if kind == 'unknown':
            self.reset()
            return Reply('', 'Nie rozumiem tego pytania lub nie mam dostępu do takich danych. '
                         'Na razie odczytuję temperaturę, wilgotność i stan klimatyzacji; '
                         'nie steruję urządzeniami.')
        self.previous, self.expires = intent, self.clock() + 120
        if room == 'unknown':
            return Reply('', 'O które pomieszczenie pytasz: salon, jadalnię czy łazienkę?')
        subject = {'temperatura': 'Temperatura', 'wilgotnosc': 'Wilgotność',
                   'ac': 'Stan klimatyzacji'}[kind]
        place = {'salon': 'salonie', 'jadalnia': 'jadalni', 'lazienka': 'łazience'}[room]
        return self.cache.answer(f'{subject} w {place}')
