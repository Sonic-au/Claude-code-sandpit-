import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aggregator.database import Base


class ItemType(str, enum.Enum):
    article = "article"
    podcast_episode = "podcast_episode"
    reddit_post = "reddit_post"
    tweet = "tweet"
    youtube_video = "youtube_video"
    newsletter = "newsletter"


class CurationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        Index("ix_items_content_hash", "content_hash"),
        Index("ix_items_canonical_url", "canonical_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    curation_status: Mapped[CurationStatus] = mapped_column(
        Enum(CurationStatus), default=CurationStatus.pending
    )
    approved_by: Mapped[str | None] = mapped_column(String(255))
    curated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source = relationship("Source", lazy="select")
    scores = relationship("Score", back_populates="item", lazy="select")
