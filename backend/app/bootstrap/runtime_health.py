from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

logger = logging.getLogger("runtime_health")

RuntimeSnapshot = Callable[[], Mapping[str, Any]]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_health_dir() -> Path:
    health_dir = Path(os.environ.get("RUNTIME_HEALTH_DIR", "/tmp/acenta-runtime-health"))
    health_dir.mkdir(parents=True, exist_ok=True)
    return health_dir


def runtime_health_path(runtime_name: str) -> Path:
    return runtime_health_dir() / f"{runtime_name}.json"


def load_runtime_health(runtime_name: str) -> dict[str, Any]:
    return json.loads(runtime_health_path(runtime_name).read_text())


def is_runtime_healthy(payload: Mapping[str, Any], *, ttl_seconds: int) -> bool:
    updated_at = payload.get("updated_at")
    if not isinstance(updated_at, str):
        return False
    if payload.get("status") != "ready":
        return False

    try:
        updated = datetime.fromisoformat(updated_at)
    except ValueError:
        return False

    now = datetime.now(timezone.utc)
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (now - updated).total_seconds() <= ttl_seconds


def install_signal_handlers(stop_event: asyncio.Event, runtime_name: str) -> None:
    loop = asyncio.get_running_loop()

    def _request_shutdown(sig_name: str) -> None:
        if not stop_event.is_set():
            logger.info("%s runtime received %s, beginning shutdown", runtime_name, sig_name)
            stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown, sig.name)
        except NotImplementedError:  # pragma: no cover - platform-specific fallback
            signal.signal(sig, lambda *_args, sig_name=sig.name: _request_shutdown(sig_name))


class RuntimeHeartbeat:
    def __init__(self, runtime_name: str, *, entrypoint: str, responsibilities: list[str]) -> None:
        self.runtime_name = runtime_name
        self.entrypoint = entrypoint
        self.responsibilities = responsibilities
        self.path = runtime_health_path(runtime_name)

    def write(self, *, status: str, details: Mapping[str, Any] | None = None) -> None:
        payload = {
            "runtime": self.runtime_name,
            "status": status,
            "entrypoint": self.entrypoint,
            "responsibilities": self.responsibilities,
            "pid": os.getpid(),
            "updated_at": _utc_now_iso(),
            "details": dict(details or {}),
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def mark_starting(self, *, details: Mapping[str, Any] | None = None) -> None:
        self.write(status="starting", details=details)

    def mark_ready(self, *, details: Mapping[str, Any] | None = None) -> None:
        self.write(status="ready", details=details)

    def mark_stopped(self, *, details: Mapping[str, Any] | None = None) -> None:
        self.write(status="stopped", details=details)


async def heartbeat_loop(
    heartbeat: RuntimeHeartbeat,
    stop_event: asyncio.Event,
    *,
    snapshot: RuntimeSnapshot,
    interval_seconds: int = 15,
) -> None:
    while not stop_event.is_set():
        heartbeat.mark_ready(details=snapshot())
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue