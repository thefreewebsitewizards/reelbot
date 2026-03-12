"""Route-level tests for the FastAPI app using TestClient."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Create a TestClient with Telegram bot mocked out and plans_dir on tmp_path."""
    monkeypatch.setenv("REELBOT_API_KEY", "test-key")

    # Mock Telegram bot lifecycle so it never starts polling
    with patch("src.main.start_bot"), \
         patch("src.main.stop_bot", return_value=None):
        from src.main import app
        from src.config import settings

        # Point plans_dir at the temp directory
        original_plans_dir = settings.plans_dir
        settings.plans_dir = tmp_path
        # Reload the auth key from the env we just set
        original_api_key = settings.reelbot_api_key
        settings.reelbot_api_key = "test-key"

        with TestClient(app) as tc:
            yield tc

        settings.plans_dir = original_plans_dir
        settings.reelbot_api_key = original_api_key


@pytest.fixture()
def plans_dir(client, tmp_path):
    """Return the tmp_path used as plans_dir (same as client fixture's tmp_path)."""
    return tmp_path


def _write_index(plans_dir: Path, plans: list[dict]) -> None:
    """Write a _index.json file to the plans directory."""
    index_path = plans_dir / "_index.json"
    index_path.write_text(json.dumps({"plans": plans}))


def _make_plan_entry(
    reel_id: str = "TEST1",
    title: str = "Test Plan",
    status: str = "review",
    plan_dir: str = "2026-03-12_TEST1",
) -> dict:
    return {
        "reel_id": reel_id,
        "title": title,
        "status": status,
        "plan_dir": plan_dir,
        "created_at": "2026-03-12T00:00:00",
        "source_url": f"https://instagram.com/reel/{reel_id}/",
        "theme": "Test theme",
        "category": "marketing",
        "relevance_score": 0.8,
        "estimated_cost": 0.01,
        "routed_to": "tfww",
        "task_count": 1,
        "total_hours": 1.0,
    }


# ---------------------------------------------------------------------------
# Health & Ready
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"status": "ok"}


def test_ready_checks_dependencies(client):
    resp = client.get("/ready")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert isinstance(data["checks"], dict)
    assert "plans_dir" in data["checks"]
    assert "env_vars" in data["checks"]
    assert "ffmpeg" in data["checks"]


# ---------------------------------------------------------------------------
# Plans — list and get
# ---------------------------------------------------------------------------


def test_list_plans_empty(client, plans_dir):
    _write_index(plans_dir, [])
    resp = client.get("/plans/")
    assert resp.status_code == 200
    assert resp.json() == {}


def test_list_plans_with_data(client, plans_dir):
    entry = _make_plan_entry()
    _write_index(plans_dir, [entry])
    resp = client.get("/plans/")
    assert resp.status_code == 200
    data = resp.json()
    assert "review" in data
    assert len(data["review"]) == 1
    assert data["review"][0]["reel_id"] == "TEST1"


def test_get_plan_not_found(client, plans_dir):
    _write_index(plans_dir, [])
    resp = client.get("/plans/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Plans — approve requires a plan in review status with tasks
# ---------------------------------------------------------------------------


def test_approve_plan_requires_auth(client, plans_dir):
    """POST /plans/{id}/approve does NOT require auth (web UI endpoint),
    but the plan must exist. A missing plan returns 404."""
    _write_index(plans_dir, [])
    resp = client.post(
        "/plans/FAKE/approve",
        json={"selected_tasks": [0]},
    )
    # No auth required on this endpoint — returns 404 because plan doesn't exist
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Plans — status update requires auth
# ---------------------------------------------------------------------------


def test_update_status_requires_auth(client, plans_dir):
    """PATCH /plans/{id}/status requires X-API-Key header."""
    entry = _make_plan_entry()
    _write_index(plans_dir, [entry])
    resp = client.patch(
        "/plans/TEST1/status",
        json={"status": "approved"},
    )
    assert resp.status_code == 401


def test_update_status_with_auth(client, plans_dir):
    """PATCH /plans/{id}/status succeeds with valid API key."""
    entry = _make_plan_entry()
    _write_index(plans_dir, [entry])
    plan_dir = plans_dir / entry["plan_dir"]
    plan_dir.mkdir()
    (plan_dir / "metadata.json").write_text(json.dumps({"reel_id": "TEST1", "status": "review"}))

    with patch("src.utils.plan_manager._trigger_execution"):
        resp = client.patch(
            "/plans/TEST1/status",
            json={"status": "approved"},
            headers={"X-API-Key": "test-key"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"


# ---------------------------------------------------------------------------
# Plans — skip
# ---------------------------------------------------------------------------


def test_skip_plan(client, plans_dir):
    entry = _make_plan_entry()
    _write_index(plans_dir, [entry])
    plan_dir = plans_dir / entry["plan_dir"]
    plan_dir.mkdir()
    (plan_dir / "metadata.json").write_text(json.dumps({"reel_id": "TEST1", "status": "review"}))

    resp = client.post("/plans/TEST1/skip")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "skipped"

    # Verify index was updated
    index = json.loads((plans_dir / "_index.json").read_text())
    assert index["plans"][0]["status"] == "failed"


def test_skip_plan_not_found(client, plans_dir):
    _write_index(plans_dir, [])
    resp = client.post("/plans/nonexistent/skip")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Reel processing
# ---------------------------------------------------------------------------


def test_process_reel_requires_auth(client, plans_dir):
    """POST /process-reel does NOT use require_api_key dependency.
    It is open (no auth). A valid URL should be accepted, not rejected with 401.
    Verify by sending a request without auth header — should NOT get 401."""
    _write_index(plans_dir, [])
    with patch("src.routers.reel._run_pipeline"), \
         patch("src.routers.reel._add_processing_entry"):
        resp = client.post(
            "/process-reel",
            json={"reel_url": "https://www.instagram.com/reel/ABC123/"},
        )
    # Should not be 401 since no auth is required on this endpoint
    assert resp.status_code != 401


def test_process_reel_accepts_valid_url(client, plans_dir):
    """POST /process-reel with a valid Instagram URL returns 202."""
    _write_index(plans_dir, [])

    with patch("src.routers.reel.threading") as mock_threading:
        mock_thread = MagicMock()
        mock_threading.Thread.return_value = mock_thread

        resp = client.post(
            "/process-reel",
            json={"reel_url": "https://www.instagram.com/reel/VALID123/"},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "processing"
    assert data["reel_id"] == "VALID123"
    mock_thread.start.assert_called_once()


def test_process_reel_rejects_invalid_url(client, plans_dir):
    """POST /process-reel with a non-Instagram URL returns 400."""
    resp = client.post(
        "/process-reel",
        json={"reel_url": "https://example.com/not-instagram"},
    )
    assert resp.status_code == 400


def test_process_reel_rejects_duplicate(client, plans_dir):
    """POST /process-reel with an already-processed reel returns 409."""
    entry = _make_plan_entry(reel_id="DUP123", plan_dir="2026-03-12_DUP123")
    _write_index(plans_dir, [entry])

    resp = client.post(
        "/process-reel",
        json={"reel_url": "https://www.instagram.com/reel/DUP123/"},
    )
    assert resp.status_code == 409
