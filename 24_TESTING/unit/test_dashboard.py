from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_state_is_read_only_and_live_disabled() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/dashboard/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "RESEARCH"
    assert payload["live_trading_allowed"] is False
    assert payload["execution_mode"] == "PAPER_FIRST"
    assert payload["risk_gate"] == "REQUIRED"
    assert payload["high_volatility_policy"] == "BLOCKED_BY_DEFAULT"
    assert payload["read_only"] is True
    assert payload["as_of"].endswith("Z")
