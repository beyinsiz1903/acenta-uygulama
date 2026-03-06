from __future__ import annotations

from app.bootstrap.runtime_health import RuntimeHeartbeat, is_runtime_healthy, load_runtime_health
from app.bootstrap.scheduler_app import get_scheduler_runtime_components
from app.bootstrap.worker_app import get_worker_runtime_components


def test_runtime_heartbeat_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNTIME_HEALTH_DIR", str(tmp_path))

    heartbeat = RuntimeHeartbeat(
        "worker",
        entrypoint="python -m app.bootstrap.worker_app",
        responsibilities=["dispatch background loops"],
    )
    heartbeat.mark_ready(details={"components": ["email-worker"]})

    payload = load_runtime_health("worker")
    assert payload["runtime"] == "worker"
    assert payload["status"] == "ready"
    assert payload["entrypoint"] == "python -m app.bootstrap.worker_app"
    assert is_runtime_healthy(payload, ttl_seconds=60) is True


def test_worker_runtime_components_respect_env(monkeypatch):
    monkeypatch.setenv("ENABLE_EMAIL_WORKER", "false")
    monkeypatch.setenv("ENABLE_INTEGRATION_SYNC_WORKER", "true")
    monkeypatch.setenv("ENABLE_JOB_WORKER", "0")

    components = {item["name"]: item for item in get_worker_runtime_components()}
    assert components["email-worker"]["enabled"] is False
    assert components["integration-sync-worker"]["enabled"] is True
    assert components["job-worker"]["enabled"] is False


def test_scheduler_runtime_components_respect_env(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("GOOGLE_SHEETS_SYNC_ENABLED", "false")

    components = {item["name"]: item for item in get_scheduler_runtime_components()}
    assert components["billing-finalize-scheduler"]["enabled"] is False
    assert components["report-check-scheduler"]["enabled"] is True
    assert components["ops-check-scheduler"]["enabled"] is True
    assert components["sheets-sync-scheduler"]["enabled"] is False
