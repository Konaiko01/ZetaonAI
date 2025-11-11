import json
import requests
import pytest

from clients.evolution_client import EvolutionClient


class DummyResponse:
    def __init__(self, status_code=200, text='OK'):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


def test_send_message_success(monkeypatch):
    sent = {}

    def fake_post(url, headers, data, timeout):
        sent['url'] = url
        sent['headers'] = headers
        sent['data'] = data
        sent['timeout'] = timeout
        return DummyResponse(200, 'sent')

    monkeypatch.setattr('requests.post', fake_post)

    client = EvolutionClient()
    client._EVOLUTION_URL = 'http://example.com'
    client._EVOLUTION_API_KEY = 'APIKEY123'
    client._EVOLUTION_SEND_PATH = '/messages'

    result = client.send_message('5511999999999', 'Olá teste')

    assert result is True
    assert sent['url'] == 'http://example.com/messages'
    payload = json.loads(sent['data'])
    assert payload['to'] == '5511999999999'
    assert payload['text']['body'] == 'Olá teste'
    assert sent['headers']['apikey'] == 'APIKEY123'


def test_send_message_timeout(monkeypatch):
    def raise_timeout(url, headers, data, timeout):
        raise requests.exceptions.Timeout('timeout')

    monkeypatch.setattr('requests.post', raise_timeout)

    client = EvolutionClient()
    client._EVOLUTION_URL = 'http://example.com'
    client._EVOLUTION_API_KEY = 'APIKEY123'
    client._EVOLUTION_SEND_PATH = '/messages'

    result = client.send_message('5511999999999', 'Olá teste')

    assert result is False
