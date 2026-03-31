from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aggregator.database import Base


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("item_id", "topic_id", name="uq_score_item_topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_high_quality: Mapped[bool] = mapped_column(Boolean, default=False)
    claude_model: Mapped[str] = mapped_column(String(100), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)

    item = relationship("Item", back_populates="scores")
    topic = relationship("Topic", lazy="select")
