from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.main import app
from app.pii import scrub_text


def test_generated_correlation_id_and_response_headers() -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json={"user_id": "qa-user", "session_id": "qa-session", "feature": "qa", "message": "Explain observability"})
    assert response.status_code == 200
    correlation_id = response.headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-fA-F]{8}", correlation_id)
    assert response.json()["correlation_id"] == correlation_id
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_valid_incoming_correlation_id_is_propagated() -> None:
    expected = "req-1a2B3c4D"
    with TestClient(app) as client:
        response = client.post("/chat", headers={"x-request-id": expected}, json={"user_id": "qa-user", "session_id": "qa-session", "feature": "qa", "message": "Explain observability"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == expected
    assert response.json()["correlation_id"] == expected


def test_log_enrichment_and_pii_redaction(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    message = "Email student@vinuni.edu.vn, phone 0987654321, card 4111 1111 1111 1111"
    with TestClient(app) as client:
        response = client.post("/chat", json={"user_id": "student-raw-id", "session_id": "session-01", "feature": "qa", "message": message})

    assert response.status_code == 200
    raw = log_path.read_text(encoding="utf-8")
    assert "student@vinuni.edu.vn" not in raw
    assert "0987654321" not in raw
    assert "4111 1111 1111 1111" not in raw

    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    request_event = next(item for item in records if item.get("event") == "request_received")
    assert request_event["correlation_id"] == response.json()["correlation_id"]
    assert request_event["session_id"] == "session-01"
    assert request_event["feature"] == "qa"
    assert request_event["model"]
    assert request_event["env"]
    assert request_event["user_id_hash"] != "student-raw-id"


def test_common_pii_types_are_scrubbed() -> None:
    text = "email=a@b.com phone=+84 987 654 321 cccd=012345678901 card=4111-1111-1111-1111 passport=B1234567 Địa chỉ: 123 Nguyễn Trãi"
    scrubbed = scrub_text(text)
    for raw in ("a@b.com", "+84 987 654 321", "012345678901", "4111-1111-1111-1111", "B1234567", "123 Nguyễn Trãi"):
        assert raw not in scrubbed
