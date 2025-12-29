from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from bson import ObjectId

from app.db import get_db


async def compute_rate_for_stay(
    tenant_id: str,
    room_type: str,
    check_in: str,
    check_out: str,
    nights: int,
    organization_id: str,
    currency: str = "TRY",
) -> list[dict[str, Any]]:
    """
    FAZ-2.2.2: Compute rates with period-based pricing
    
    Priority:
    1. Rate period override (date + days_of_week + min_stay match)
    2. Rate plan default_price (optional, not implemented yet)
    3. Room type base_price (fallback)
    
    Returns list of applicable rate plans with calculated prices
    """
    db = await get_db()
    
    # Parse dates (STRING → date object, CRITICAL!)
    search_check_in = date.fromisoformat(check_in)
    search_check_out = date.fromisoformat(check_out)
    
    # 1. Fetch active rate plans for this room type
    rate_plans = await db.rate_plans.find({
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "is_active": True,
    }).sort("priority", 1).to_list(100)
    
    # Filter by applies_to_room_types
    applicable_plans = []
    for plan in rate_plans:
        applies_to = plan.get("applies_to_room_types")
        if applies_to is None or room_type in applies_to:
            applicable_plans.append(plan)
    
    # 2. Fetch all active periods for these plans
    plan_ids = [plan["_id"] for plan in applicable_plans]
    
    if not plan_ids:
        # No rate plans → fallback to base_price
        return []
    
    periods = await db.rate_periods.find({
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "rate_plan_id": {"$in": plan_ids},
        "is_active": True,
    }).to_list(500)
    
    # 3. For each rate plan, calculate price
    rate_results = []
    
    for plan in applicable_plans:
        plan_id = plan["_id"]
        plan_periods = [p for p in periods if p.get("rate_plan_id") == plan_id]
        
        # Calculate price for each night
        total_price = 0.0
        night_count = 0
        current_date = search_check_in
        
        while current_date < search_check_out:
            # Find matching period for this date
            matched_period = None
            
            for period in sorted(plan_periods, key=lambda p: p.get("priority", 100)):
                # Parse period dates (STRING → date)
                p_start = date.fromisoformat(period["start_date"])
                p_end_str = period.get("end_date")
                p_end = date.fromisoformat(p_end_str) if p_end_str else None
                
                # Date overlap check
                date_match = p_start <= current_date and (p_end is None or current_date < p_end)
                
                if not date_match:
                    continue
                
                # days_of_week check
                dow_list = period.get("days_of_week")
                if dow_list is not None:
                    if current_date.weekday() not in dow_list:
                        continue
                
                # min_stay check
                min_stay = period.get("min_stay")
                if min_stay and nights < min_stay:
                    continue
                
                # Match found!
                matched_period = period
                break
            
            if matched_period:
                price = matched_period.get("price_per_night", 0)
            else:
                # Fallback to base_price (will be calculated separately)
                price = 0
            
            total_price += price
            night_count += 1
            current_date = current_date + timedelta(days=1)
        
        # If no periods matched, skip this plan (will fallback to base_price)
        if total_price == 0:
            continue
        
        # Calculate average per_night
        avg_per_night = round(total_price / nights, 2) if nights > 0 else 0
        
        rate_results.append({
            "rate_plan_id": str(plan_id),
            "rate_plan_name": plan.get("name", "Rate Plan"),
            "board": plan.get("board", "RO"),
            "cancellation": plan.get("cancellation_policy_type", "FREE_CANCEL"),
            "price": {
                "total": round(total_price, 2),
                "per_night": avg_per_night,
                "currency": currency,
                "tax_included": True,
            },
        })
    
    return rate_results
