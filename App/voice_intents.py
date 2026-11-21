"""Ground natural home questions in explicit readings/rooms before using a small LLM."""
import re

from App.voice_queries import normalize, question_words

KINDS = {'temperatura', 'wilgotnosc', 'ac', 'klimat'}
ROOM_PATTERNS = {
    'salon': r'\bsalon\w*\b|\bpokoj\w* dzien\w*\b',
    'jadalnia': r'\bjadaln\w*\b',
    'lazienka': r'\blazien\w*\b',
}
UNSUPPORTED = (r'\b(?:sypial\w*|kuch\w*|garaz\w*|gabinet\w*|piwnic\w*|korytarz\w*|'
               r'taras\w*|balkon\w*|biur\w*|kotlown\w*|poddasz\w*|grzejnik\w*|kaloryfer\w*|bojler\w*|boiler\w*|ariston\w*|pralk\w*|'
               r'prad\w*|energ\w*|zuzyc\w*|pogod\w*|deszcz\w*|zewn\w*|hasl\w*|password|token|'
               r'ustaw\w*|nastaw\w*|docelow\w*|zadan(?:a|ej|e|y|ego)|zignoruj|ignoruj|instrukcj\w*)\b')
COMMANDS = {'wlacz', 'wylacz', 'wlaczaj', 'wylaczaj', 'wlaczyc', 'wylaczyc',
            'uruchom', 'uruchomic', 'zmien', 'zmienic', 'podnies', 'obniz', 'zwieksz', 'zmniejsz'}


def intent(kind, room):
    return {'kind': kind, 'room': room}


def entities(text):
    text = normalize(text)
    rooms = {room for room, pattern in ROOM_PATTERNS.items() if re.search(pattern, text)}
    kinds = set()
    if re.search(r'\b(?:temperatur\w*|stopn\w*|ciepl\w*|chlodn\w*|zimn\w*)\b', text):
        kinds.add('temperatura')
    if re.search(r'\b(?:wilgo\w*|such\w*)\b', text):
        kinds.add('wilgotnosc')
    if re.search(r'\b(?:klima|klimy|klime|klimie|klimatyzac\w*|klimatyzator\w*|airstage)\b', text):
        kinds.add('ac')
    return kinds, rooms


def resolve(text, previous=None):
    """Return None only for language that still needs model interpretation."""
    normalized = normalize(text)
    words = set(re.findall(r'\w+', normalized))
    if words & COMMANDS or re.search(UNSUPPORTED, normalized):
        return intent('unknown', 'unknown')
    kinds, rooms = entities(text)
    previous = previous or {}
    room = next(iter(rooms)) if len(rooms) == 1 else 'unknown'
    if len(rooms) > 1:
        room = 'unknown'  # Always ask instead of choosing an arbitrary room.
    elif not rooms and previous.get('room') in ROOM_PATTERNS:
        # A new, unrecognized place must not silently become the previous room.
        elsewhere = re.search(r'\b(?:w|we|na)\s+(?!tej chwili\b|tym momencie\b|'
                              r'tym samym pokoj\w*\b|ogole\b|przyklad\b|temat\b|teraz\b)\w+', normalized)
        if not elsewhere:
            room = previous['room']
    if kinds == {'temperatura', 'wilgotnosc'}:
        return intent('klimat', room)
    if len(kinds) == 1:
        return intent(next(iter(kinds)), room)
    if len(kinds) > 1:
        return intent('clarify', room)
    if rooms:
        # A bare room is a reply to a room question or an explicit follow-up.
        tokens = question_words(text)
        followup = len(tokens) <= 5 and all(w in {
            'a', 'w', 'we', 'salon', 'salonie', 'salonu', 'jadalnia', 'jadalni',
            'lazienka', 'lazience', 'lazienki', 'tym', 'samym', 'pokoju'} for w in tokens)
        kind = previous.get('kind') if followup else None
        return intent(kind if kind in KINDS else 'clarify', room)
    if normalized.strip(' ?.!') in ('a tam', 'a tam jak', 'a w tym samym pokoju'):
        return intent(previous.get('kind', 'clarify'), room)
    if re.search(r'\b(?:czujnik\w*|odczyt\w*|pomiar\w*|powietrz\w*)\b', normalized):
        return intent('clarify', room)
    return None


class GroundedIntentClient:
    """A model may interpret, but cannot invent a room or silently choose a reading."""
    def __init__(self, model):
        self.model = model
        self.model_calls = 0

    async def classify(self, text, previous=None):
        resolved = resolve(text, previous)
        if resolved is not None:
            return resolved
        self.model_calls += 1
        proposed = await self.model.classify(text, previous)
        if proposed['kind'] == 'unknown':
            return proposed
        # No explicit reading was recognized. Ask the user to name it instead
        # of trusting the small model's guess (observed in the Pi benchmark).
        _, rooms = entities(text)
        room = next(iter(rooms)) if len(rooms) == 1 else (previous or {}).get('room', 'unknown')
        return intent('clarify', room)
