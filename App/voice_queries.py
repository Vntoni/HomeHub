"""Bounded Polish read-only questions over cached values; no device handles."""
from dataclasses import dataclass
import re
import unicodedata

from Ports.sensor import sensor_measurement


@dataclass(frozen=True)
class Reply:
    understood: str
    answer: str


ROOMS = {'salon': 'Salon', 'jadalnia': 'Jadalnia', 'lazienka': 'Łazienka'}
ALIASES = {
    'jaka': 'jaka', 'jaki': 'jaka', 'jakie': 'jaka', 'jest': 'jest',
    'ile': 'ile', 'w': 'w', 'czy': 'czy', 'jak': 'jaka', 'mamy': 'jest',
    'cieplo': 'temperatura', 'zimno': 'temperatura',
    'wilgotno': 'wilgotnosc', 'sucho': 'wilgotnosc', 'klima': 'ac',
    'temperatura': 'temperatura', 'temperatury': 'temperatura', 'stopni': 'temperatura',
    'wilgotnosc': 'wilgotnosc', 'wilgotnosci': 'wilgotnosc',
    'stan': 'stan', 'status': 'stan',
    'klimatyzacja': 'ac', 'klimatyzacji': 'ac', 'klimatyzator': 'ac', 'klimatyzatora': 'ac',
    'wlaczona': 'wlaczona', 'wlaczony': 'wlaczona', 'dziala': 'wlaczona', 'pracuje': 'wlaczona',
    'wylaczona': 'wylaczona', 'wylaczony': 'wylaczona',
    'salon': 'salon', 'salonie': 'salon', 'jadalnia': 'jadalnia', 'jadalni': 'jadalnia',
    'lazienka': 'lazienka', 'lazience': 'lazienka',
}
# Never approximate negation, verbs, numbers or arbitrary device names.
FUZZY = {word: value for word, value in ALIASES.items()
         if value in {*ROOMS, 'temperatura', 'wilgotnosc', 'ac'} and len(word) >= 5}
HELP = ('Zapytaj np. „Jaka jest temperatura w łazience?”, „Jaka jest wilgotność '
        'w łazience?” lub „Czy klimatyzacja w salonie jest włączona?”. '
        'Podaj jeden pokój: salon, jadalnia albo łazienka. Na tym etapie tylko odczytuję dane.')


def normalize(text):
    text = unicodedata.normalize('NFKD', text.lower().replace('ł', 'l'))
    return ''.join(c for c in text if not unicodedata.combining(c))


def one_edit(left, right):
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    short, long = sorted((left, right), key=len)
    return any(long[:i] + long[i + 1:] == short for i in range(len(long)))


def edit_distance(left, right):
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def question_words(text):
    words = re.findall(r'\w+', normalize(text))
    # Only remove polite/read introductions, never negation or device commands.
    for phrase in (['pokoju', 'dziennym'], ['pokoj', 'dzienny']):
        for i in range(len(words) - 1):
            if words[i:i+2] == phrase:
                words[i:i+2] = ['salon']
                break
    prefixes = (
        ['czy', 'moglbys', 'mi', 'powiedziec'], ['czy', 'moglabys', 'mi', 'powiedziec'],
        ['czy', 'mozesz', 'mi', 'powiedziec'], ['mozesz', 'mi', 'powiedziec'],
        ['powiedz', 'mi'], ['powiedz'], ['prosze'], ['sprawdz'],
        ['podaj', 'mi'], ['podaj'], ['pokaz'],
    )
    # Introductions can stack: "proszę, powiedz mi...".
    while words:
        prefix = next((p for p in prefixes if words[:len(p)] == p), None)
        if prefix is None:
            break
        words = words[len(prefix):]
    return words


def parse_question(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 300:
        return None
    words = question_words(text)
    if len(words) > 14:
        return None
    tokens, corrections = [], 0
    for word in words:
        value = ALIASES.get(word)
        if value is None and len(word) >= 5 and corrections == 0:
            candidates = {value for known, value in FUZZY.items()
                          if one_edit(word, known) or
                          (value == 'ac' and len(word) >= 10 and len(known) >= 10
                           and edit_distance(word, known) <= 2)}
            if len(candidates) == 1:
                value = candidates.pop()
                corrections += 1
        if value is None:
            return None
        tokens.append(value)
    tokens = tuple(tokens)
    for room in ROOMS:
        for kind in ('temperatura', 'wilgotnosc'):
            prefixes = [('jaka', 'jest', kind), ('jaka', kind), ('jaka', kind, 'jest'), (kind,)]
            if kind == 'temperatura':
                prefixes += [('ile', 'jest', kind), ('ile', kind), ('ile', kind, 'jest')]
            if tokens in {prefix + ('w', room) for prefix in prefixes}:
                return kind, room, bool(corrections)
        if tokens in {
            ('jaka', 'jest', 'stan', 'ac', 'w', room), ('stan', 'ac', 'w', room),
            *(('czy', 'ac', 'w', room, 'jest', state) for state in ('wlaczona', 'wylaczona')),
            *(('czy', 'ac', 'jest', state, 'w', room) for state in ('wlaczona', 'wylaczona')),
            ('czy', 'wlaczona', 'ac', 'w', room), ('czy', 'ac', 'wlaczona', 'w', room), ('czy', 'ac', 'w', room, 'wlaczona'),
        }:
            return 'ac', room, bool(corrections)
    return None


class ReadOnlyHomeQueries:
    def __init__(self):
        self.sensors = {}
        self.ac_temperature = {}
        self.ac_mode = {}
        self.ac_stale = {}
        self.ac_online = {}

    def sensor(self, room, field, value):
        room = normalize(room)
        if room in ROOMS and field in ('temperature', 'humidity'):
            self.sensors[room, field] = sensor_measurement({field: value}, field)

    def indoor(self, room, value):
        room = normalize(room)
        if room in ('salon', 'jadalnia'):
            self.ac_temperature[room] = sensor_measurement({'temperature': value}, 'temperature')

    def mode(self, room, value):
        room = normalize(room)
        if room in ('salon', 'jadalnia'):
            self.ac_mode[room] = value if value in ('OFF', 'AUTO', 'COOL', 'DRY', 'FAN', 'HEAT') else None

    def stale(self, kind, room, value):
        if kind == 'ac':
            self.ac_stale[normalize(room)] = bool(value)

    def online(self, room, value):
        self.ac_online[normalize(room)] = bool(value)

    def answer(self, text):
        parsed = parse_question(text)
        if parsed is None:
            if isinstance(text, str) and len(text) <= 300 and tuple(question_words(text)) in {
                ('jaka', 'jest', 'temperatura'), ('jaka', 'temperatura'), ('temperatura',),
                ('jaka', 'jest', 'wilgotnosc'), ('wilgotnosc',),
                ('czy', 'klimatyzacja', 'jest', 'wlaczona'), ('stan', 'klimatyzacji'),
            }:
                return Reply('', 'O które pomieszczenie pytasz: salon, jadalnię czy łazienkę?')
            return Reply('', 'Nie rozumiem jednoznacznie pytania. ' + HELP)
        kind, room, corrected = parsed
        label = ROOMS[room]
        subject = {'temperatura': 'Temperatura', 'wilgotnosc': 'Wilgotność', 'ac': 'Stan klimatyzacji'}[kind]
        understood = f'{subject} — {label}' + (' (dopasowano drobną literówkę)' if corrected else '')
        if kind == 'ac':
            mode = self.ac_mode.get(room)
            if mode is None:
                return Reply(understood, f'{label}: brak danych o stanie klimatyzacji.')
            value = 'wyłączona' if mode == 'OFF' else 'włączona'
            answer = f'{label}: ostatni znany stan klimatyzacji — {value}.'
            return Reply(understood, answer + self._ac_freshness(room))
        field = 'temperature' if kind == 'temperatura' else 'humidity'
        value = self.sensors.get((room, field))
        source = 'czujnik Zigbee'
        freshness = ' Czas wykonania pomiaru nie jest znany.'
        if value is None and kind == 'temperatura':
            value = self.ac_temperature.get(room)
            source = 'klimatyzacja'
            freshness = self._ac_freshness(room)
        if value is None:
            return Reply(understood, f'{label}: brak danych. HomeHub nie ma zapisanego odczytu dla tego pytania.')
        number = f'{value:.1f}'.replace('.', ',')
        unit = '°C' if kind == 'temperatura' else '%'
        return Reply(understood, f'{label}: ostatni znany odczyt — {number} {unit} '
                     f'(źródło: {source}).' + freshness)

    def _ac_freshness(self, room):
        if self.ac_stale.get(room, True) or self.ac_online.get(room) is False:
            return ' Dane mogą być nieaktualne; odśwież urządzenia, aby je potwierdzić.'
        return ' To odczyt z pamięci HomeHub, bez nowego połączenia z urządzeniem.'
