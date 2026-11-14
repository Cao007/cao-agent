from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.modules.chat.schemas import ChatInput, ThreadCreate, ThreadInfo  # noqa: F401

Intent = Literal["knowledge", "order", "logistics", "refund", "greeting"]


class SupportProfile(BaseModel):
    is_operator: bool
    mode: str
    threshold: float


class OrderInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    number: str
    product: str
    status: str
    delivered_days: int | None
    opened: bool
    logistics: str


class Citation(BaseModel):
    number: int
    knowledge_id: UUID
    title: str
    content: str
    score: float


class SupportMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    turn_id: UUID | None = None
    citations: list[Citation] = []
    tools: list[str] = []
    confidence: float | None = None
    feedback: str | None = None
    handoff: bool = False


class SupportThread(ThreadInfo):
    messages: list[SupportMessage]
    orders_to_select: list[OrderInfo] = []
    can_retry: bool = False


class OrderSelection(BaseModel):
    order_id: UUID


class FeedbackInput(BaseModel):
    value: Literal["up", "down"]


class KnowledgeInput(BaseModel):
    title: str = Field(min_length=1, max_length=120, pattern=r"\S")
    content: str = Field(min_length=1, max_length=32000, pattern=r"\S")
    category: Literal["faq", "refund", "shipping", "product"] = "faq"


class KnowledgeInfo(KnowledgeInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    index_mode: str
    chunk_count: int
    progress: int


class ReviewInput(BaseModel):
    action: Literal["approve", "reject", "expire"]
    answer: str = Field(default="", max_length=32000)


class TurnInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    question: str
    answer: str
    intent: str
    review_status: str | None
    correction: str | None
    handoff: bool
    feedback: str | None
    created_at: datetime


class EvaluationInput(BaseModel):
    question: str = Field(min_length=1, max_length=1000, pattern=r"\S")
    expected_knowledge_id: UUID | None = None
    intent: Intent
    source: str = Field(default="运营录入", min_length=1, max_length=120)


class EvaluationInfo(EvaluationInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class StrategyMetric(BaseModel):
    strategy: str
    recall: float
    mrr: float
    coverage: float
    count: int


class EvaluationResult(BaseModel):
    mode: str
    dataset_size: int
    sources: list[str]
    strategies: list[StrategyMetric]
    classifier_accuracy: float
    confusion: dict[str, dict[str, int]]
    recommended_threshold: float
    threshold_accuracy: float
    created_at: datetime | None = None


class IntentUsage(BaseModel):
    intent: str
    calls: int
    input_tokens: int
    output_tokens: int
    measured_calls: int
    estimated_cost_usd: float | None


class Dashboard(BaseModel):
    knowledge_count: int
    indexed_count: int
    pending_count: int
    handoff_count: int
    conversations: int
    mode: str
    threshold: float
    evaluation: EvaluationResult | None
    usage: list[IntentUsage]
    topics: dict[str, int]
