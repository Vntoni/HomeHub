import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from PySide6.QtCore import QCoreApplication

from Adapters.local_intent import LocalIntentClient, validate_intent, parse_content
from App.local_agent import LocalHomeAgent
from App.voice_queries import ReadOnlyHomeQueries, Reply
from Interface.qt_audio_probe import AudioProbeController


@pytest.mark.parametrize('value', [None, [], {}, {'kind': 'shell', 'room': 'salon'},
    {'kind': 'ac', 'room': 'bedroom'}, {'kind': 'unknown', 'room': 'salon'},
    {'kind': 'ac', 'room': 'salon', 'answer': '23'}, {'kind': [], 'room': 'salon'}])
def test_invalid_intents(value):
    with pytest.raises(ValueError):
        validate_intent(value)


async def test_local_http_contract_and_no_readings_sent():
    def handler(request):
        assert str(request.url) == 'http://127.0.0.1:9081/v1/chat/completions'
        payload = json.loads(request.content)
        assert payload['max_tokens'] == 80
        assert 'response_format' not in payload
        assert payload['cache_prompt'] is True
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'content': '{"kind":"temperatura","room":"lazienka"}'}}]})
    result = await LocalIntentClient(transport=httpx.MockTransport(handler)).classify('Ile stopni w łazience?')
    assert result == {'kind': 'temperatura', 'room': 'lazienka'}


@pytest.mark.parametrize('response', [httpx.Response(503), httpx.Response(200, content=b'x'*17000),
    httpx.Response(200, json={'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}),
    httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': '23 stopnie'}}]})])
async def test_bad_server_responses_fail_closed(response):
    client = LocalIntentClient(transport=httpx.MockTransport(lambda _: response))
    with pytest.raises((ValueError, httpx.HTTPError)):
        await client.classify('Ciepło?')


async def test_grounded_values_followup_expiry_and_outage():
    now = [1]
    cache = ReadOnlyHomeQueries()
    cache.sensor('lazienka', 'temperature', 20.6)
    client = AsyncMock()
    agent = LocalHomeAgent(cache, client, clock=lambda: now[0])
    assert '20,6' in (await agent.answer('Temperatura w łazience')).answer
    client.classify.assert_not_called()
    client.classify.return_value = {'kind': 'wilgotnosc', 'room': 'lazienka'}
    assert 'brak danych' in (await agent.answer('A wilgotność?')).answer
    assert client.classify.call_args.args[1] == {'kind': 'temperatura', 'room': 'lazienka'}
    now[0] = 400
    await agent.answer('A wilgotność?')
    assert client.classify.call_args.args[1] is None
    client.classify.side_effect = TimeoutError()
    assert 'niedostępny' in (await agent.answer('Ciepło?')).answer
    assert agent.previous is None
    assert '20,6' in (await agent.answer('Temperatura w łazience')).answer


async def test_clarification_unsupported_and_reset():
    client = AsyncMock()
    agent = LocalHomeAgent(ReadOnlyHomeQueries(), client)
    client.classify.return_value = {'kind': 'temperatura', 'room': 'unknown'}
    assert 'pomieszczenie' in (await agent.answer('Jak ciepło?')).answer
    client.classify.return_value = {'kind': 'temperatura', 'room': 'salon'}
    assert 'brak danych' in (await agent.answer('W salonie')).answer
    client.classify.return_value = {'kind': 'unknown', 'room': 'unknown'}
    assert 'nie steruję' in (await agent.answer('Włącz ogrzewanie')).answer
    assert agent.previous is None


async def test_async_answer_does_not_block_and_close_discards_late_result():
    app = QCoreApplication.instance() or QCoreApplication([])
    started, release = asyncio.Event(), asyncio.Event()
    async def answer(text):
        started.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            pass
        return Reply('late', 'late')
    probe = AudioProbeController(answerer=answer)
    probe.openPanel()
    probe.editQuestion('Ciepło?')
    probe.askQuestion()
    await started.wait()
    assert probe.busy
    probe.closePanel()
    release.set()
    await probe.aclose()
    assert not probe.answer and not probe.question


async def test_close_before_async_answer_starts():
    app = QCoreApplication.instance() or QCoreApplication([])
    answerer = AsyncMock(return_value=Reply('unused', 'unused'))
    probe = AudioProbeController(answerer=answerer)
    probe.openPanel()
    probe.editQuestion('Test')
    probe.askQuestion()
    probe.closePanel()
    await probe.aclose()
    answerer.assert_not_awaited()
    assert not probe.answer


@pytest.mark.parametrize('text', [
    'Proszę powiedz mi jaka jest temperatura w salonie',
    'Proszę, czy możesz mi powiedzieć, jaka jest temperatura w salonie?',
    'Czy mógłbyś mi powiedzieć jaka jest temperatura w salonie?',
])
async def test_stacked_polite_introductions_take_fast_path(text):
    client = AsyncMock()
    cache = ReadOnlyHomeQueries()
    cache.indoor('salon', 21.5)
    agent = LocalHomeAgent(cache, client)
    assert '21,5' in (await agent.answer(text)).answer
    client.classify.assert_not_called()


async def test_unclear_reading_asks_then_keeps_room_for_reply():
    client = AsyncMock()
    client.classify.side_effect = [{'kind': 'clarify', 'room': 'salon'},
                                   {'kind': 'temperatura', 'room': 'salon'}]
    cache = ReadOnlyHomeQueries()
    cache.indoor('salon', 22)
    agent = LocalHomeAgent(cache, client)
    reply = await agent.answer('Jak tam w salonie?')
    assert 'Co chcesz sprawdzić w salonie' in reply.answer
    reply = await agent.answer('Chodzi mi o temperaturę')
    assert '22,0' in reply.answer
    assert client.classify.call_args.args[1] == {'kind': 'clarify', 'room': 'salon'}


async def test_two_readings_and_long_natural_question_use_real_values():
    client = AsyncMock()
    client.classify.return_value = {'kind': 'klimat', 'room': 'lazienka'}
    cache = ReadOnlyHomeQueries()
    cache.sensor('lazienka', 'temperature', 20.6)
    cache.sensor('lazienka', 'humidity', 65)
    agent = LocalHomeAgent(cache, client)
    text = 'Wiesz co, mam do ciebie takie pytanie, ' * 10 + 'sprawdź temperaturę i wilgotność w łazience.'
    reply = await agent.answer(text)
    client.classify.assert_awaited_once_with(text, None)
    assert '20,6' in reply.answer and '65,0' in reply.answer


async def test_expired_clarification_does_not_supply_old_room():
    now = [1]
    client = AsyncMock()
    client.classify.return_value = {'kind': 'clarify', 'room': 'salon'}
    agent = LocalHomeAgent(ReadOnlyHomeQueries(), client, clock=lambda: now[0])
    await agent.answer('Jak tam?')
    now[0] += 301
    client.classify.return_value = {'kind': 'wilgotnosc', 'room': 'unknown'}
    assert 'pomieszczenie' in (await agent.answer('Chodzi mi o wilgotność')).answer
    assert client.classify.call_args.args[1] is None


@pytest.mark.parametrize('prefix', ['', '</think>', '<think></think>'])
def test_observed_empty_thinking_marker_is_accepted(prefix):
    assert parse_content(prefix + '{"kind":"temperatura","room":"salon"}') == {
        'kind': 'temperatura', 'room': 'salon'}


@pytest.mark.parametrize('content', [
    '<think>Może 23 stopnie</think>{"kind":"temperatura","room":"salon"}',
    'Odpowiedź: {"kind":"temperatura","room":"salon"}',
    '{"kind":"temperatura","room":"salon","value":23}',
    '</think>{"kind":"temperatura","room":"salon"} trailing text',
])
def test_no_intent_is_extracted_from_arbitrary_model_prose(content):
    with pytest.raises(ValueError): parse_content(content)
