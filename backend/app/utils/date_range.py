from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from pydantic import BaseModel


class DateRangePeriod(BaseModel):
    """Date range period for API responses"""
    start: str  # YYYY-MM-DD
    end: str    # YYYY-MM-DD
    days: int


def now_utc() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)


def parse_date_range(
    start: Optional[str],
    end: Optional[str],
    days: Optional[int],
    default_days: int = 30,
    max_days: int = 365,
) -> Tuple[datetime, datetime, int]:
    """
    Parse date range from query params with backward compatibility.
    
    Priority:
    1. If start or end is provided, use date range (end is inclusive)
    2. Otherwise, use days parameter
    
    Args:
        start: Start date (YYYY-MM-DD, inclusive)
        end: End date (YYYY-MM-DD, inclusive)
        days: Number of days back from now
        default_days: Default if nothing provided
        max_days: Maximum allowed days
        
    Returns:
        (cutoff_date, end_date, actual_days)
    """
    
    # Priority 1: Date range
    if start or end:
        try:
            # Parse start date
            if start:
                start_dt = datetime.strptime(start, "%Y-%m-%d")
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            else:
                # If only end is given, default to 30 days before end
                end_dt_temp = datetime.strptime(end, "%Y-%m-%d") if end else now_utc()
                start_dt = end_dt_temp - timedelta(days=default_days)
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            
            # Parse end date (inclusive, so add 1 day for exclusive upper bound)
            if end:
                end_dt = datetime.strptime(end, "%Y-%m-%d")
                end_dt = end_dt.replace(tzinfo=timezone.utc)
                # Make exclusive (end day included in results)
                end_dt = end_dt + timedelta(days=1)
            else:
                # If only start is given, default to now
                end_dt = now_utc()
            
            # Calculate actual days
            delta = end_dt - start_dt
            actual_days = max(1, delta.days)
            
            return start_dt, end_dt, actual_days
            
        except ValueError:
            # Invalid date format, fall back to days
            pass
    
    # Priority 2: Days parameter (backward compatible)
    days_val = days or default_days
    days_val = min(max(days_val, 1), max_days)
    
    end_dt = now_utc()
    start_dt = end_dt - timedelta(days=days_val)
    
    return start_dt, end_dt, days_val


def format_date_range(start: datetime, end: datetime) -> dict:
    """
    Format date range for API response.
    
    Returns:
        {
            "start": "YYYY-MM-DD",
            "end": "YYYY-MM-DD",
            "days": N
        }
    """
    # Adjust end back by 1 day since we made it exclusive
    end_inclusive = end - timedelta(days=1)
    
    delta = end - start
    days = max(1, delta.days)
    
    return {
        "start": start.strftime("%Y-%m-%d"),
        "end": end_inclusive.strftime("%Y-%m-%d"),
        "days": days,
    }
