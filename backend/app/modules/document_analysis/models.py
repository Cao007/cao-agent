from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[UUID] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    require_review: Mapped[bool]
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
