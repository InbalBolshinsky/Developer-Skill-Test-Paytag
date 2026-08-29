from dataclasses import dataclass, field
from datetime import datetime

from paytag_client.api.models import Item


@dataclass
class Basket:
    items: list[Item] = field(default_factory=list)
    last_confirmed_at: datetime | None = None
    is_stale: bool = False

    @staticmethod
    def from_items(items: list[Item], confirmed_at: datetime) -> "Basket":
        deduplicated = list({item.rfid: item for item in items}.values())
        return Basket(items=deduplicated, last_confirmed_at=confirmed_at, is_stale=False)

    def mark_stale(self) -> None:
        self.is_stale = True

    def neutralizable_items(self) -> list[Item]:
        return [item for item in self.items if not item.is_hard_tag]

    def hard_tag_items(self) -> list[Item]:
        return [item for item in self.items if item.is_hard_tag]
