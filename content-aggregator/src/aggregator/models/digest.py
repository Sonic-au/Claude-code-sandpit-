import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from aggregator.database import Base


class DigestType(str, enum.Enum):
    email = "email"
    slack = "slack"


class DigestStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class DigestRun(Base):
    __tablename__ = "digest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_type: Mapped[DigestType] = mapped_column(Enum(DigestType), nullable=False)
    topic_ids: Mapped[list] = mapped_column(JSON, default=list)
    item_ids: Mapped[list] = mapped_column(JSON, default=list)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    recipient: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[DigestStatus] = mapped_column(
        Enum(DigestStatus), default=DigestStatus.pending
    )
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
