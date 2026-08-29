from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from paytag_client.api.models import ErrorCode


class TransactionStatus(str, Enum):
    CLOSED = "closed"
    ABORTED = "aborted"


class ItemFinalStatus(str, Enum):
    NEUTRALIZED = "neutralized"
    FAILED = "failed"
    HARD_TAG_PENDING_REMOVAL = "hard_tag_pending_removal"


@dataclass(frozen=True)
class TransactionItemRecord:
    barcode: str
    rfid: str
    is_hard_tag: bool
    final_status: ItemFinalStatus


@dataclass(frozen=True)
class TransactionOutcome:
    error_code: ErrorCode | None
    error_message: str | None


@dataclass
class Transaction:
    transaction_number: str
    run_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: TransactionStatus | None = None
    items: list[TransactionItemRecord] = field(default_factory=list)
    outcome: TransactionOutcome | None = None
    read_issue_count: int = 0
    last_read_issue_at: datetime | None = None
