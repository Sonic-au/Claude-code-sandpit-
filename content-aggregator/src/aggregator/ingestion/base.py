from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawItem:
    url: str
    title: str
    body: str
    item_type: str
    external_id: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


class AbstractSourceAdapter(ABC):
    def __init__(self, source_config: dict) -> None:
        self.config = source_config

    @abstractmethod
    async def fetch(self) -> list[RawItem]:
        """Fetch items from the source. Returns a list of RawItem instances."""
        ...
