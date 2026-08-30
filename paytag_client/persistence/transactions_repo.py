from datetime import datetime

from pymongo.collection import Collection

from paytag_client.domain.transaction import (
    Transaction,
    TransactionItemRecord,
    TransactionOutcome,
    TransactionStatus,
)


class TransactionRepository:
    def __init__(self, collection: Collection):
        self._collection = collection
        # Index supports status queries (hard tags pending removal, failed items) without a full scan.
        self._collection.create_index("items.final_status")

    def insert_started(self, transaction: Transaction) -> None:
        # Write the full skeleton up front so every later write is a pure $set on an existing doc.
        self._collection.insert_one({
            "_id": transaction.transaction_number,
            "run_id": transaction.run_id,
            "started_at": transaction.started_at,
            "ended_at": None,
            "status": None,
            "items": [],
            "outcome": None,
            "read_issue_count": 0,
            "last_read_issue_at": None,
        })

    def mark_closed(
        self,
        transaction_number: str,
        ended_at: datetime,
        items: list[TransactionItemRecord],
        outcome: TransactionOutcome,
    ) -> None:
        result = self._collection.update_one(
            {"_id": transaction_number},
            {"$set": {
                "status": TransactionStatus.CLOSED.value,
                "ended_at": ended_at,
                "items": [self._item_to_doc(item) for item in items],
                "outcome": {
                    "error_code": int(outcome.error_code) if outcome.error_code is not None else None,
                    "error_message": outcome.error_message,
                },
            }},
        )
        self._require_matched(result.matched_count, transaction_number)

    def mark_aborted(self, transaction_number: str, ended_at: datetime) -> None:
        result = self._collection.update_one(
            {"_id": transaction_number},
            {"$set": {"status": TransactionStatus.ABORTED.value, "ended_at": ended_at}},
        )
        self._require_matched(result.matched_count, transaction_number)

    def record_read_issue(self, transaction_number: str, at: datetime) -> None:
        result = self._collection.update_one(
            {"_id": transaction_number},
            {"$inc": {"read_issue_count": 1}, "$set": {"last_read_issue_at": at}},
        )
        self._require_matched(result.matched_count, transaction_number)

    @staticmethod
    def _item_to_doc(item: TransactionItemRecord) -> dict:
        return {
            "barcode": item.barcode,
            "rfid": item.rfid,
            "is_hard_tag": item.is_hard_tag,
            "final_status": item.final_status.value,
        }

    @staticmethod
    def _require_matched(matched_count: int, transaction_number: str) -> None:
        # A missing document mid-run (e.g. dropped collection) is a hard error, not a silent no-op.
        if matched_count == 0:
            raise ValueError(f"No transaction document found for transaction_number={transaction_number!r}")
