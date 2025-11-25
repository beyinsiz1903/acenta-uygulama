"""
Advanced Revenue Management Models
AI-powered pricing, forecasting, yield management
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, date
from enum import Enum
import uuid

class PricingStrategy(str, Enum):
    """Fiyatlandırma stratejisi"""
    AGGRESSIVE = "aggressive"  # Yüksek fiyat, yüksek gelir
    BALANCED = "balanced"  # Dengeli
    OCCUPANCY_FOCUSED = "occupancy_focused"  # Doluluk odaklı

class DemandLevel(str, Enum):
    """Talep seviyesi"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
