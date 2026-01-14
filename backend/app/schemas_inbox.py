from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, constr


class InboxChannel(str, Enum):
    email = "email"
    whatsapp = "whatsapp"
    sms = "sms"
    internal = "internal"


class InboxThreadStatus(str, Enum):
    open = "open"
    pending = "pending"
    done = "done"


class InboxDirection(str, Enum):
    incoming = "in"
    outgoing = "out"
    internal = "internal"


class ParticipantBase(BaseModel):
    customer_id: Optional[str] = None
    contact_type: Optional[str] = None
    contact_value: Optional[str] = None


class ParticipantIn(ParticipantBase):
    pass


class ParticipantOut(ParticipantBase):
    pass


class ThreadSummaryOut(BaseModel):
    id: str
    organization_id: str
    channel: str
    subject: Optional[str] = None
    status: str
    customer_id: Optional[str] = None
    participants: List[ParticipantOut] = Field(default_factory=list)
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    message_count: int


class MessageOut(BaseModel):
    id: str
    organization_id: str
    thread_id: str
    direction: str
    body: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    actor_user_id: Optional[str] = None
    actor_roles: List[str] = Field(default_factory=list)
    source: str = "api"
    created_at: datetime


class PaginatedThreadsOut(BaseModel):
    items: List[ThreadSummaryOut]
    total: int
    page: int
    page_size: int


class PaginatedMessagesOut(BaseModel):
    items: List[MessageOut]
    total: int
    page: int
    page_size: int


class CreateThreadRequest(BaseModel):
    channel: InboxChannel
    subject: Optional[str] = None
    participants: List[ParticipantIn] = Field(default_factory=list)
    customer_id: Optional[str] = None


class CreateMessageRequest(BaseModel):
    direction: InboxDirection
    body: constr(min_length=1)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
