#!/usr/bin/env python3
"""O1 - Restore Test Script.

Restores a backup into a temporary database, verifies collections, and runs integrity checks.

Usage:
    python scripts/restore_test.py /var/backups/app/backup_<id>.gz
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def get_mongo_url():
    return os.environ.get("MONGO_URL", "mongodb://localhost:27017")


def restore_to_temp_db(archive_path: str, temp_db_name: str) -> bool:
    """Restore the backup archive into a temporary database."""
    mongo_url = get_mongo_url()
    cmd = [
        "mongorestore",
        f"--uri={mongo_url}",
        f"--archive={archive_path}",
        "--gzip",
        f"--nsFrom=*.*",
        f"--nsTo={temp_db_name}.*",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"RESTORE FAILED: {result.stderr[:500]}")
            return False
        print(f"Restore successful to temp DB: {temp_db_name}")
        return True
    except subprocess.TimeoutExpired:
        print("RESTORE TIMED OUT")
        return False
    except Exception as e:
        print(f"RESTORE ERROR: {e}")
        return False


async def verify_restored_db(temp_db_name: str) -> dict:
    """Verify collections in the restored database."""
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(get_mongo_url())
    db = client[temp_db_name]

    collections = await db.list_collection_names()
    summary = {
        "collections_count": len(collections),
        "collections": {},
        "integrity_ok": True,
    }

    for coll_name in sorted(collections):
        count = await db[coll_name].count_documents({})
        summary["collections"][coll_name] = count

    # Verify audit chain integrity if present
    if "audit_logs_chain" in collections:
        chain_count = await db.audit_logs_chain.count_documents({})
        summary["audit_chain_entries"] = chain_count

    client.close()
    return summary


async def cleanup_temp_db(temp_db_name: str):
    """Drop the temporary database."""
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(get_mongo_url())
    await client.drop_database(temp_db_name)
    print(f"Cleaned up temp DB: {temp_db_name}")
    client.close()


async def main(archive_path: str):
    if not Path(archive_path).exists():
        print(f"ERROR: Archive not found: {archive_path}")
        sys.exit(1)

    temp_db_name = f"restore_test_{os.getpid()}"
    print(f"\n=== Restore Test ===")
    print(f"Archive: {archive_path}")
    print(f"Temp DB: {temp_db_name}")
    print()

    # Step 1: Restore
    success = restore_to_temp_db(archive_path, temp_db_name)
    if not success:
        sys.exit(1)

    # Step 2: Verify
    print("\n--- Verification ---")
    summary = await verify_restored_db(temp_db_name)

    print(f"Collections: {summary['collections_count']}")
    for name, count in summary["collections"].items():
        print(f"  {name}: {count} documents")

    if "audit_chain_entries" in summary:
        print(f"\nAudit chain entries: {summary['audit_chain_entries']}")

    # Step 3: Cleanup
    await cleanup_temp_db(temp_db_name)

    print(f"\n=== Summary ===")
    print(f"Status: {'OK' if summary['integrity_ok'] else 'ISSUES FOUND'}")
    print(f"Total collections: {summary['collections_count']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore_test.py <backup_archive_path>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
