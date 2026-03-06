from __future__ import annotations

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bootstrap.runtime_init import load_backend_env

logger = logging.getLogger("scheduler_runtime")


async def _build_report_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def _check_due_reports() -> None:
        try:
            from app.services.report_scheduler import execute_due_schedules

            await execute_due_schedules()
        except Exception as exc:
            logging.getLogger("report_scheduler").error("Report schedule check failed: %s", exc)

    scheduler.add_job(_check_due_reports, "interval", minutes=15, id="report_check")
    return scheduler


async def _build_ops_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def _check_uptime() -> None:
        try:
            from app.services.uptime_service import check_and_log_uptime

            await check_and_log_uptime()
        except Exception as exc:
            logging.getLogger("ops_scheduler").error("Uptime check failed: %s", exc)

    async def _verify_audit_chains() -> None:
        try:
            from app.services.integrity_service import verify_all_audit_chains

            await verify_all_audit_chains()
        except Exception as exc:
            logging.getLogger("ops_scheduler").error("Audit chain verify failed: %s", exc)

    async def _verify_ledger() -> None:
        try:
            from app.services.integrity_service import verify_ledger_integrity

            await verify_ledger_integrity()
        except Exception as exc:
            logging.getLogger("ops_scheduler").error("Ledger integrity check failed: %s", exc)

    async def _cleanup_backups() -> None:
        try:
            from app.services.backup_service import cleanup_old_backups

            await cleanup_old_backups()
        except Exception as exc:
            logging.getLogger("ops_scheduler").error("Backup cleanup failed: %s", exc)

    scheduler.add_job(_check_uptime, "interval", minutes=1, id="uptime_check")
    scheduler.add_job(_verify_audit_chains, "cron", hour=3, minute=0, id="audit_chain_verify")
    scheduler.add_job(_verify_ledger, "cron", hour=3, minute=30, id="ledger_integrity")
    scheduler.add_job(_cleanup_backups, "cron", hour=4, minute=0, id="backup_cleanup")
    return scheduler


async def _build_sheets_scheduler() -> AsyncIOScheduler | None:
    if os.environ.get("GOOGLE_SHEETS_SYNC_ENABLED", "true").lower() != "true":
        return None

    from app.db import get_db

    interval = int(os.environ.get("GOOGLE_SHEETS_SYNC_INTERVAL_MINUTES", "5"))
    scheduler = AsyncIOScheduler()

    async def _run_sheets_sync() -> None:
        try:
            from app.services.sheet_sync_service import run_scheduled_sync

            db = await get_db()
            count = await run_scheduled_sync(db)
            if count > 0:
                logging.getLogger("sheets_sync").info("Synced %d legacy sheet connections", count)
        except Exception as exc:
            logging.getLogger("sheets_sync").error("Legacy sheets sync error: %s", exc)

    async def _run_portfolio_sync() -> None:
        try:
            from app.services.hotel_portfolio_sync_service import run_scheduled_portfolio_sync

            db = await get_db()
            result = await run_scheduled_portfolio_sync(db)
            total = result.get("total", 0)
            if total > 0:
                logging.getLogger("portfolio_sync").info(
                    "Portfolio sync: total=%d success=%d failed=%d",
                    total,
                    result.get("success", 0),
                    result.get("failed", 0),
                )
        except Exception as exc:
            logging.getLogger("portfolio_sync").error("Portfolio sync error: %s", exc)

    async def _process_writebacks() -> None:
        try:
            from app.services.sheet_writeback_service import process_pending_writebacks

            db = await get_db()
            result = await process_pending_writebacks(db)
            total = result.get("total", 0)
            if total > 0:
                logging.getLogger("sheet_writeback").info(
                    "Write-back processed: total=%d completed=%d failed=%d",
                    total,
                    result.get("completed", 0),
                    result.get("failed", 0),
                )
        except Exception as exc:
            logging.getLogger("sheet_writeback").error("Write-back processor error: %s", exc)

    scheduler.add_job(_run_sheets_sync, "interval", minutes=interval, id="sheets_sync")
    scheduler.add_job(_run_portfolio_sync, "interval", minutes=interval, id="portfolio_sync")
    scheduler.add_job(_process_writebacks, "interval", seconds=30, id="writeback_processor")
    return scheduler


async def main() -> None:
    load_backend_env()

    from app.billing.scheduler import start_scheduler, stop_scheduler
    from app.bootstrap.runtime_init import init_observability, load_sheets_config_from_db, shutdown_runtime_resources
    from app.db import close_mongo, connect_mongo, get_db

    init_observability()
    await connect_mongo()

    schedulers: list[AsyncIOScheduler] = []
    try:
        db = await get_db()
        await load_sheets_config_from_db(db)

        start_scheduler()

        report_scheduler = await _build_report_scheduler()
        report_scheduler.start()
        schedulers.append(report_scheduler)

        ops_scheduler = await _build_ops_scheduler()
        ops_scheduler.start()
        schedulers.append(ops_scheduler)

        sheets_scheduler = await _build_sheets_scheduler()
        if sheets_scheduler is not None:
            sheets_scheduler.start()
            schedulers.append(sheets_scheduler)

        logger.info("Scheduler runtime started with %d schedulers", len(schedulers) + 1)
        await asyncio.Event().wait()
    finally:
        for scheduler in reversed(schedulers):
            if scheduler.running:
                scheduler.shutdown(wait=False)
        stop_scheduler()
        shutdown_runtime_resources()
        await close_mongo()


if __name__ == "__main__":
    asyncio.run(main())