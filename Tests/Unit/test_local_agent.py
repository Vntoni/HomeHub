import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from PySide6.QtCore import QCoreApplication

from Adapters.local_intent import LocalIntentClient, validate_intent
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
        assert payload['response_format']['json_schema']['strict']
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
    now[0] = 200
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
