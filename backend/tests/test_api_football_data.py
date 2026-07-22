import pytest
import requests

from src.api_football_data import football_data_org as football_data_org_module


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_api_request_retries_after_ssl_error(monkeypatch):
    call_count = {"value": 0}

    def fake_get(url, headers=None, params=None, timeout=30):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise requests.exceptions.SSLError("ssl handshake failed")
        return DummyResponse({"status": "ok"})

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(football_data_org_module.requests, "get", fake_get)
    monkeypatch.setattr(football_data_org_module.asyncio, "sleep", fake_sleep)

    response = await football_data_org_module.api_request("standings", 2000)

    assert response == {"status": "ok"}
    assert call_count["value"] == 2
