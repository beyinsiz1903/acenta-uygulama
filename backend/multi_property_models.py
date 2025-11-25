"""
Multi-Property Management Models
Çoklu otel yönetimi, merkezi rezervasyon
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid

class PropertyGroup(BaseModel):
    """Otel grubu"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    group_name: str
    headquarters_location: str
    total_properties: int = 0
    total_rooms: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConsolidatedMetrics(BaseModel):
    """Birleştirilmiş metrikler"""
    group_id: str
    report_date: datetime
    
    # Occupancy
    total_rooms: int
    total_occupied: int
    group_occupancy_pct: float
    
    # Revenue
    total_revenue: float
    total_adr: float
    total_revpar: float
    
    # By property
    property_breakdown: List[dict] = []
    
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
