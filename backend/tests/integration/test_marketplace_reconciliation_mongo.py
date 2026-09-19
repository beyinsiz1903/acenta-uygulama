"""Real Mongo lease tests. Run with --noconftest; never use configured DB URLs.

Starts its own localhost-only mongod in pytest's temporary directory. PMS lookup
is mocked so only atomic claim/finalize behavior is under integration test.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import shutil
import socket
import subprocess
import time
import uuid
from unittest.mock import AsyncMock

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import pytest

from app.services.syroce import reconciliation as recon


@pytest.fixture(scope="module")
def isolated_mongo(tmp_path_factory):
    binary = shutil.which("mongod")
    if not binary:
        pytest.skip("mongod executable required for isolated Mongo integration tests")
    directory = tmp_path_factory.mktemp("marketplace-reconciliation-mongo")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    uri = f"mongodb://127.0.0.1:{port}/?directConnection=true"
    process = subprocess.Popen(
        [
            binary,
            "--dbpath",
            str(directory),
            "--bind_ip",
            "127.0.0.1",
            "--port",
            str(port),
            "--nounixsocket",
            "--logpath",
            str(directory / "mongod.log"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    probe = MongoClient(uri, serverSelectionTimeoutMS=200)
    try:
        deadline = time.monotonic() + 15
        while True:
            if process.poll() is not None:
                pytest.fail(
                    "Isolated mongod exited before startup; inspect temporary mongod.log"
                )
            try:
                probe.admin.command("ping")
                break
            except ConnectionFailure:
                if time.monotonic() >= deadline:
                    pytest.fail("Isolated mongod did not start within 15 seconds")
                time.sleep(0.05)
        yield uri
    finally:
        probe.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def run_scenario(uri, scenario):
    async def run():
        client = AsyncIOMotorClient(uri, tz_aware=True, serverSelectionTimeoutMS=1000)
        db = client[f"reconciliation_{uuid.uuid4().hex}"]
        try:
            await db[recon.COLLECTION].insert_one(
                {
                    "id": "local-1",
                    "organization_id": "org-1",
                    "channel": "syroce_marketplace",
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc) - timedelta(minutes=10),
                }
            )
            await asyncio.wait_for(scenario(db), timeout=10)
        finally:
            client.close()

    asyncio.run(run())


def test_two_workers_only_one_lookup(isolated_mongo, monkeypatch):
    async def scenario(db):
        entered, release = asyncio.Event(), asyncio.Event()

        async def lookup(client, local):
            entered.set()
            await release.wait()
            return {
                "status": "confirmed",
                "syroce_reservation_id": "pms-1",
                "reconciliation_required": False,
            }

        lookup_mock = AsyncMock(side_effect=lookup)
        monkeypatch.setattr(recon, "verified_update", lookup_mock)
        factory = AsyncMock(return_value=object())
        first = asyncio.create_task(recon.reconcile_one(db, client_factory=factory))
        await entered.wait()
        try:
            assert await recon.reconcile_one(db, client_factory=factory) is False
        finally:
            release.set()
            await first
        lookup_mock.assert_awaited_once()
        factory.assert_awaited_once_with("org-1")
        doc = await db[recon.COLLECTION].find_one({"id": "local-1"})
        assert doc["status"] == "confirmed"
        assert doc["reconciliation_attempts"] == 1
        assert "reconciliation_token" not in doc

    run_scenario(isolated_mongo, scenario)


@pytest.mark.parametrize("race", ["new_owner", "normal_completion", "lease_expired"])
def test_stale_worker_cannot_overwrite(isolated_mongo, monkeypatch, race):
    async def scenario(db):
        collection = db[recon.COLLECTION]
        entered, release = asyncio.Event(), asyncio.Event()

        async def lookup(client, local):
            entered.set()
            await release.wait()
            return {"status": "cancelled", "syroce_reservation_id": "stale-result"}

        monkeypatch.setattr(recon, "verified_update", lookup)
        factory = AsyncMock(return_value=object())
        first = asyncio.create_task(recon.reconcile_one(db, client_factory=factory))
        await entered.wait()
        try:
            if race == "normal_completion":
                await collection.update_one(
                    {"id": "local-1"},
                    {
                        "$set": {
                            "status": "confirmed",
                            "syroce_reservation_id": "normal-result",
                        }
                    },
                )
            else:
                await collection.update_one(
                    {"id": "local-1"},
                    {
                        "$set": {
                            "reconciliation_lease_until": datetime.now(timezone.utc)
                            - timedelta(seconds=1)
                        }
                    },
                )
                if race == "new_owner":
                    monkeypatch.setattr(
                        recon,
                        "verified_update",
                        AsyncMock(
                            return_value={
                                "status": "confirmed",
                                "syroce_reservation_id": "new-owner-result",
                            }
                        ),
                    )
                    assert await recon.reconcile_one(db, client_factory=factory)
        finally:
            release.set()
            await first
        doc = await collection.find_one({"id": "local-1"})
        if race == "lease_expired":
            assert doc["status"] == "pending"
            assert "syroce_reservation_id" not in doc
            assert "reconciliation_attempts" not in doc
        else:
            assert doc["status"] == "confirmed"
            assert doc["syroce_reservation_id"] == (
                "normal-result" if race == "normal_completion" else "new-owner-result"
            )
            assert doc.get("reconciliation_attempts", 0) == (
                1 if race == "new_owner" else 0
            )

    run_scenario(isolated_mongo, scenario)


def test_cancelled_process_claim_recovers_after_expiry(isolated_mongo, monkeypatch):
    async def scenario(db):
        entered = asyncio.Event()

        async def lookup(client, local):
            entered.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(recon, "verified_update", lookup)
        factory = AsyncMock(return_value=object())
        task = asyncio.create_task(recon.reconcile_one(db, client_factory=factory))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert await recon.reconcile_one(db, client_factory=factory) is False
        await db[recon.COLLECTION].update_one(
            {"id": "local-1"},
            {
                "$set": {
                    "reconciliation_lease_until": datetime.now(timezone.utc)
                    - timedelta(seconds=1)
                }
            },
        )
        monkeypatch.setattr(
            recon, "verified_update", AsyncMock(return_value={"status": "confirmed"})
        )
        assert await recon.reconcile_one(db, client_factory=factory)
        doc = await db[recon.COLLECTION].find_one({"id": "local-1"})
        assert doc["status"] == "confirmed"
        assert doc["reconciliation_attempts"] == 1

    run_scenario(isolated_mongo, scenario)


def test_unresolved_retry_cooldown_and_bounded_history(isolated_mongo, monkeypatch):
    async def scenario(db):
        collection = db[recon.COLLECTION]
        monkeypatch.setattr(recon, "verified_update", AsyncMock(return_value=None))
        factory = AsyncMock(return_value=object())
        for attempt in range(25):
            assert await recon.reconcile_one(db, client_factory=factory)
            assert await recon.reconcile_one(db, client_factory=factory) is False
            doc = await collection.find_one({"id": "local-1"})
            assert doc["status"] == "pending"
            assert doc["reconciliation_attempts"] == attempt + 1
            assert len(doc["reconciliation_history"]) == min(attempt + 1, 20)
            assert doc["reconciliation_next_at"] - doc[
                "reconciliation_checked_at"
            ] == timedelta(minutes=5)
            await collection.update_one(
                {"id": "local-1"},
                {
                    "$set": {
                        "reconciliation_next_at": datetime.now(timezone.utc)
                        - timedelta(seconds=1)
                    }
                },
            )

    run_scenario(isolated_mongo, scenario)
