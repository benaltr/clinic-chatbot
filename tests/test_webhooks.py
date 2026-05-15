from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tenants.models import ClinicConfig


@pytest.fixture(autouse=True)
def patch_registry(demo_clinic):
    """Replace the live registry with one containing our test clinic."""
    from app.tenants.registry import registry
    registry._by_number = {demo_clinic.whatsapp.number: demo_clinic}
    registry._by_id = {demo_clinic.clinic_id: demo_clinic}
    yield
    registry._by_number = {}
    registry._by_id = {}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_meta_webhook_verify_valid(client):
    resp = client.get(
        "/webhook/meta",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == 12345


def test_meta_webhook_verify_wrong_token(client):
    resp = client.get(
        "/webhook/meta",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 403


def test_meta_webhook_receive_returns_200(client, meta_payload):
    with (
        patch("app.api.webhooks.message_service.handle_incoming", new=AsyncMock()),
        patch("app.api.webhooks.get_db"),
    ):
        resp = client.post("/webhook/meta", json=meta_payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
