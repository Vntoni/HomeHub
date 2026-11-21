from unittest.mock import AsyncMock

import pytest

from App.voice_intents import GroundedIntentClient, resolve
from Tools.benchmark_local_agent import cases
from App.local_agent import LocalHomeAgent
from App.voice_queries import ReadOnlyHomeQueries


@pytest.mark.parametrize('text,previous,expected', list(cases()))
async def test_grounded_homehub_benchmark(text, previous, expected):
    model = AsyncMock()
    model.classify.return_value = {'kind': 'unknown', 'room': 'unknown'}
    client = GroundedIntentClient(model)
    assert await client.classify(text, previous) == expected


@pytest.mark.parametrize('text,kind,room', [
    ('Mógłbyś zerknąć, bo trochę mi zimno, jaka jest temperatura w salonie?', 'temperatura', 'salon'),
    ('Proszę sprawdź mi, jak bardzo wilgotno jest w łazience', 'wilgotnosc', 'lazienka'),
    ('Powiedz mi, czy klimatyzator w jadalni przypadkiem nie jest wyłączony?', 'ac', 'jadalnia'),
    ('Jestem ciekaw temperatury oraz wilgotności w pokoju dziennym', 'klimat', 'salon'),
    ('Jak tam odczyty w salonie?', 'clarify', 'salon'),
    ('Sprawdź odczyty temperatury w salonie oraz jadalni', 'temperatura', 'unknown'),
    ('Czy możesz mi uruchomić klimatyzację?', 'unknown', 'unknown'),
    ('Podaj temperaturę w kuchni', 'unknown', 'unknown'),
])
def test_additional_paraphrases(text, kind, room):
    # Unsupported/ambiguous explicit entities never inherit an old room.
    assert resolve(text, {'kind': 'ac', 'room': 'lazienka'}) == {'kind': kind, 'room': room}


async def test_model_cannot_invent_measurement_type_or_room():
    model = AsyncMock()
    model.classify.return_value = {'kind': 'temperatura', 'room': 'salon'}
    client = GroundedIntentClient(model)
    assert await client.classify('Czy wszystko jest w porządku?') == {'kind':'clarify','room':'unknown'}
    model.classify.assert_awaited_once()


async def test_clarification_and_followups_use_cache_without_model():
    model = AsyncMock()
    cache = ReadOnlyHomeQueries()
    cache.sensor('lazienka', 'humidity', 65)
    client = GroundedIntentClient(model)
    agent = LocalHomeAgent(cache, client)
    assert 'pomieszczenie' in (await agent.answer('Sprawdź wilgotność')).answer
    assert '65,0' in (await agent.answer('W łazience')).answer
    assert 'Co chcesz sprawdzić w salonie' in (await agent.answer('Jak tam w salonie?')).answer
    assert 'brak danych' in (await agent.answer('Chodzi mi o temperaturę')).answer
    model.classify.assert_not_called()


async def test_short_social_replies_do_not_call_model_or_lose_room():
    model = AsyncMock()
    agent = LocalHomeAgent(ReadOnlyHomeQueries(), GroundedIntentClient(model))
    await agent.answer('Jak tam w salonie?')
    assert 'Nie ma sprawy' in (await agent.answer('Dziękuję!')).answer
    assert agent.previous == {'kind':'clarify', 'room':'salon'}
    assert 'Cześć' in (await agent.answer('Hej')).answer
    model.classify.assert_not_called()
