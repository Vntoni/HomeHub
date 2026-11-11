from unittest.mock import Mock

import pytest
import requests

from atlantic_client import AtlanticCozytouchClient


def response(status, data):
    return Mock(status_code=status, json=Mock(return_value=data), text="fake response")


@pytest.fixture
def transport(monkeypatch):
    client = AtlanticCozytouchClient("fake-user", "fake-password")
    monkeypatch.setattr(client, "_ensure_logged_in", lambda: True)
    monkeypatch.setattr(client, "_handle_auth_error", Mock(return_value=True))
    post = Mock(return_value=response(201, {"id": 123}))
    get = Mock(return_value=response(200, {"state": "COMPLETED"}))
    monkeypatch.setattr("atlantic_client.requests.post", post)
    monkeypatch.setattr("atlantic_client.requests.get", get)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    return client, post, get


@pytest.mark.parametrize("state", ["UNKNOWN", "IN_PROGRESS", "FAILED", "ERROR", None, "future-state"])
def test_only_confirmed_completion_is_success(transport, state):
    client, post, get = transport
    get.return_value = response(200, {"state": state})
    assert client.set_capability(10, 40, "20") is False
    post.assert_called_once()
    assert get.call_count <= 20


@pytest.mark.parametrize("data", [{}, None, [], "", False])
def test_created_without_execution_id_is_unconfirmed(transport, data):
    client, post, get = transport
    post.return_value = response(201, data)
    assert client.set_capability(10, 40, "20") is False
    post.assert_called_once()
    get.assert_not_called()


@pytest.mark.parametrize("state", ["COMPLETED", 3, "3"])
def test_delayed_completion_preserves_existing_supported_encodings(transport, state):
    client, post, get = transport
    get.side_effect = [response(200, {"state": "IN_PROGRESS"}), response(200, {"state": state})]
    assert client.set_capability(10, 40, "20") is True
    post.assert_called_once()
    assert get.call_count == 2


def test_status_auth_retry_only_repeats_read(transport):
    client, post, get = transport
    get.side_effect = [response(401, {}), response(200, {"state": "COMPLETED"})]
    assert client.set_capability(10, 40, "20") is True
    post.assert_called_once()
    assert get.call_count == 2


@pytest.mark.parametrize("failure", ["timeout", "invalid-json", "unavailable"])
def test_unreadable_status_is_not_success_or_repeated_write(transport, failure):
    client, post, get = transport
    if failure == "timeout":
        get.side_effect = requests.Timeout("fake timeout")
    elif failure == "invalid-json":
        get.return_value.json.side_effect = ValueError("fake invalid json")
    else:
        get.return_value = response(503, {})
    assert client.set_capability(10, 40, "20") is False
    post.assert_called_once()


def test_write_auth_failure_does_not_automatically_repeat_command(transport):
    client, post, get = transport
    post.side_effect = [response(401, {}), response(201, {"id": 456})]
    assert client.set_capability(10, 40, "20") is False
    post.assert_called_once()
    get.assert_not_called()
