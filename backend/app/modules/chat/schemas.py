from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ThreadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(default="新会话", min_length=1, max_length=120)


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=16000)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ThreadInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    status: str
    created_at: datetime


class ThreadDetail(ThreadInfo):
    messages: list[Message]
