"""O1 - Backup & Restore Service.

Provides full MongoDB backup via mongodump, retention policy, and listing.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc

BACKUP_DIR = Path("/var/backups/app")
RETENTION_DAYS = 30


def _ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _mongo_url() -> str:
    return os.environ.get("MONGO_URL", "mongodb://localhost:27017")


def _db_name() -> str:
    return os.environ.get("DB_NAME", "test_database")


async def run_full_backup(backup_type: str = "manual") -> dict[str, Any]:
    """Run a full MongoDB backup using mongodump."""
    _ensure_backup_dir()
    db = await get_db()

    backup_id = str(uuid.uuid4())
    filename = f"backup_{backup_id}.gz"
    filepath = BACKUP_DIR / filename

    doc = {
        "_id": backup_id,
        "backup_id": backup_id,
        "type": backup_type,
        "filename": filename,
        "size_bytes": 0,
        "created_at": now_utc(),
        "status": "running",
        "error_message": None,
    }
    await db.system_backups.insert_one(doc)

    try:
        mongo_uri = _mongo_url()
        db_name = _db_name()
        cmd = [
            "mongodump",
            f"--uri={mongo_uri}",
            f"--db={db_name}",
            f"--archive={str(filepath)}",
            "--gzip",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")[:500]
            await db.system_backups.update_one(
                {"_id": backup_id},
                {"$set": {"status": "failed", "error_message": error_msg}},
            )
            return {**doc, "status": "failed", "error_message": error_msg}

        size_bytes = filepath.stat().st_size if filepath.exists() else 0
        await db.system_backups.update_one(
            {"_id": backup_id},
            {"$set": {"status": "completed", "size_bytes": size_bytes}},
        )
        doc["status"] = "completed"
        doc["size_bytes"] = size_bytes
        return doc

    except asyncio.TimeoutError:
        await db.system_backups.update_one(
            {"_id": backup_id},
            {"$set": {"status": "failed", "error_message": "Backup timed out after 300s"}},
        )
        return {**doc, "status": "failed", "error_message": "Backup timed out"}
    except Exception as e:
        error_msg = str(e)[:500]
        await db.system_backups.update_one(
            {"_id": backup_id},
            {"$set": {"status": "failed", "error_message": error_msg}},
        )
        return {**doc, "status": "failed", "error_message": error_msg}


async def list_backups(skip: int = 0, limit: int = 50) -> list[dict[str, Any]]:
    """List all backups, newest first."""
    db = await get_db()
    cursor = db.system_backups.find().sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    # Serialize datetime
    for item in items:
        if isinstance(item.get("created_at"), datetime):
            item["created_at"] = item["created_at"].isoformat()
    return items


async def delete_backup(backup_id: str) -> bool:
    """Delete a backup file and its DB record."""
    db = await get_db()
    doc = await db.system_backups.find_one({"_id": backup_id})
    if not doc:
        return False

    # Delete file if exists
    filepath = BACKUP_DIR / doc.get("filename", "")
    if filepath.exists():
        filepath.unlink()

    await db.system_backups.delete_one({"_id": backup_id})
    return True


async def cleanup_old_backups() -> int:
    """Delete backups older than RETENTION_DAYS. Returns count deleted."""
    db = await get_db()
    cutoff = now_utc() - timedelta(days=RETENTION_DAYS)

    old_backups = await db.system_backups.find(
        {"created_at": {"$lt": cutoff}}
    ).to_list(length=1000)

    deleted = 0
    for backup in old_backups:
        filepath = BACKUP_DIR / backup.get("filename", "")
        if filepath.exists():
            filepath.unlink()
        await db.system_backups.delete_one({"_id": backup["_id"]})
        deleted += 1

    return deleted
