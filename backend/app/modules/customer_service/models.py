from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


class Operator(Base):
    __tablename__ = "support_operators"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class Knowledge(Base):
    __tablename__ = "support_knowledge"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), default="faq")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    index_mode: Mapped[str] = mapped_column(String(100), default="demo")
    chunks: Mapped[list] = mapped_column(JSONB, default=list)


class Order(Base):
    __tablename__ = "support_orders"
    __table_args__ = (UniqueConstraint("user_id", "number"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    number: Mapped[str] = mapped_column(String(32))
    product: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32))
    delivered_days: Mapped[int | None]
    opened: Mapped[bool] = mapped_column(default=False)
    logistics: Mapped[str] = mapped_column(Text)


class Turn(Base):
    __tablename__ = "support_turns"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(32))
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    tools: Mapped[list] = mapped_column(JSONB, default=list)
    usage: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float]
    feedback: Mapped[str | None] = mapped_column(String(8))
    review_status: Mapped[str | None] = mapped_column(String(16), index=True)
    correction: Mapped[str | None] = mapped_column(Text)
    handoff: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class EvaluationCase(Base):
    __tablename__ = "support_evaluation_cases"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    question: Mapped[str] = mapped_column(Text)
    expected_knowledge_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("support_knowledge.id", ondelete="SET NULL")
    )
    intent: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(120))


class EvaluationRun(Base):
    __tablename__ = "support_evaluation_runs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    result: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
