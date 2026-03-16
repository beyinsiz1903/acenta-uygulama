"""Sync Job State Machine — P4.2.

Defines all valid job states and transitions for supplier sync operations.

States:
  pending                    — Job created, waiting to start
  running                    — Job is actively syncing
  completed                  — All records synced successfully
  completed_with_partial_errors — Some records failed, successful ones preserved
  failed                     — Job failed entirely
  retry_scheduled            — Failed job queued for automatic retry
  stuck                      — Job exceeded max duration (guard detected)
  cancelled                  — Job cancelled by operator

Transitions:
  pending → running
  running → completed | completed_with_partial_errors | failed | stuck
  failed → retry_scheduled | cancelled
  completed_with_partial_errors → retry_scheduled
  retry_scheduled → running
  stuck → retry_scheduled | cancelled
"""
from __future__ import annotations


class SyncJobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_PARTIAL_ERRORS = "completed_with_partial_errors"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    STUCK = "stuck"
    CANCELLED = "cancelled"

    ALL = [
        PENDING, RUNNING, COMPLETED, COMPLETED_WITH_PARTIAL_ERRORS,
        FAILED, RETRY_SCHEDULED, STUCK, CANCELLED,
    ]

    # Which statuses are considered "terminal" (no auto-transition)
    TERMINAL = [COMPLETED, CANCELLED]

    # Which statuses are eligible for retry
    RETRYABLE = [FAILED, COMPLETED_WITH_PARTIAL_ERRORS, STUCK]

    # Which statuses indicate an active/in-progress job
    ACTIVE = [PENDING, RUNNING, RETRY_SCHEDULED]


# Valid state transitions
VALID_TRANSITIONS: dict[str, list[str]] = {
    SyncJobStatus.PENDING: [SyncJobStatus.RUNNING, SyncJobStatus.CANCELLED],
    SyncJobStatus.RUNNING: [
        SyncJobStatus.COMPLETED,
        SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS,
        SyncJobStatus.FAILED,
        SyncJobStatus.STUCK,
    ],
    SyncJobStatus.FAILED: [SyncJobStatus.RETRY_SCHEDULED, SyncJobStatus.CANCELLED],
    SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS: [SyncJobStatus.RETRY_SCHEDULED],
    SyncJobStatus.RETRY_SCHEDULED: [SyncJobStatus.RUNNING, SyncJobStatus.CANCELLED],
    SyncJobStatus.STUCK: [SyncJobStatus.RETRY_SCHEDULED, SyncJobStatus.CANCELLED],
    SyncJobStatus.COMPLETED: [],
    SyncJobStatus.CANCELLED: [],
}


# Retry configuration
RETRY_CONFIG = {
    "max_retries": 3,
    "retry_delay_seconds": 60,
    "retry_backoff_multiplier": 2.0,
    "max_retry_delay_seconds": 600,
    "stuck_threshold_minutes": 5,
}

# Region sync configuration
REGION_SYNC_CONFIG = {
    "ratehawk": [
        {"id": "2998", "name": "Antalya", "country": "TR"},
        {"id": "8359", "name": "Istanbul", "country": "TR"},
        {"id": "8316", "name": "Bodrum", "country": "TR"},
        {"id": "6040", "name": "Dubai", "country": "AE"},
        {"id": "8326", "name": "Belek", "country": "TR"},
    ],
    "paximum": [
        {"id": "antalya", "name": "Antalya", "country": "TR"},
        {"id": "istanbul", "name": "Istanbul", "country": "TR"},
        {"id": "bodrum", "name": "Bodrum", "country": "TR"},
    ],
    "wtatil": [
        {"id": "antalya", "name": "Antalya", "country": "TR"},
    ],
    "tbo": [
        {"id": "antalya", "name": "Antalya", "country": "TR"},
        {"id": "dubai", "name": "Dubai", "country": "AE"},
    ],
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Check if a state transition is valid."""
    return to_status in VALID_TRANSITIONS.get(from_status, [])


def is_retryable(status: str) -> bool:
    """Check if a job in this status can be retried."""
    return status in SyncJobStatus.RETRYABLE


def is_active(status: str) -> bool:
    """Check if a job is currently active."""
    return status in SyncJobStatus.ACTIVE
