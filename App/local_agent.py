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
        if not isinstance(text, str) or not text.strip() or len(text) > 1600:
            return Reply('', 'Powiedz pytanie w jednej wypowiedzi, do trzydziestu sekund.')
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
        self.previous, self.expires = intent, self.clock() + 300
        if kind == 'clarify':
            location = {'salon': 'w salonie', 'jadalnia': 'w jadalni',
                        'lazienka': 'w łazience', 'unknown': 'w domu'}[room]
            return Reply('', f'Co chcesz sprawdzić {location}: temperaturę, wilgotność czy stan klimatyzacji?')
        if room == 'unknown':
            return Reply('', 'O które pomieszczenie pytasz: salon, jadalnię czy łazienkę?')
        if kind == 'klimat':
            place = {'salon': 'salonie', 'jadalnia': 'jadalni', 'lazienka': 'łazience'}[room]
            replies = [self.cache.answer(f'{subject} w {place}') for subject in ('Temperatura', 'Wilgotność')]
            return Reply('Temperatura i wilgotność — ' + {'salon': 'Salon', 'jadalnia': 'Jadalnia',
                         'lazienka': 'Łazienka'}[room], ' '.join(reply.answer for reply in replies))
        subject = {'temperatura': 'Temperatura', 'wilgotnosc': 'Wilgotność',
                   'ac': 'Stan klimatyzacji'}[kind]
        place = {'salon': 'salonie', 'jadalnia': 'jadalni', 'lazienka': 'łazience'}[room]
        return self.cache.answer(f'{subject} w {place}')
