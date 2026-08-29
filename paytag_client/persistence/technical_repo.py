from datetime import datetime

from pymongo.collection import Collection

from paytag_client.api.models import ErrorCode, HealthStatus


class TechnicalRepository:
    def __init__(self, collection: Collection):
        self._collection = collection
        self._collection.create_index([("run_id", 1), ("type", 1)])

    def log_run_started(self, run_id: str, started_at: datetime) -> None:
        self._collection.insert_one({
            "type": "run_started",
            "run_id": run_id,
            "started_at": started_at,
        })

    def log_run_ended(self, run_id: str, ended_at: datetime) -> None:
        self._collection.insert_one({
            "type": "run_ended",
            "run_id": run_id,
            "ended_at": ended_at,
        })

    def log_health_check(self, run_id: str, timestamp: datetime, health: HealthStatus) -> None:
        self._collection.insert_one({
            "type": "health_check",
            "run_id": run_id,
            "timestamp": timestamp,
            "version": health.version,
            "reader_status": health.reader_connected,
            "neutralizer_status": health.neutralizer_connected,
            "all_connected": health.all_connected,
        })

    def log_poll_failure(
        self,
        run_id: str,
        transaction_number: str,
        timestamp: datetime,
        endpoint: str,
        error_code: ErrorCode | None,
        error_message: str | None,
    ) -> None:
        self._collection.insert_one({
            "type": "poll_failure",
            "run_id": run_id,
            "transaction_number": transaction_number,
            "timestamp": timestamp,
            "endpoint": endpoint,
            "error_code": int(error_code) if error_code is not None else None,
            "error_message": error_message,
        })

    def log_app_event(
        self,
        run_id: str,
        timestamp: datetime,
        level: str,
        message: str,
        transaction_number: str | None = None,
    ) -> None:
        doc = {
            "type": "app_log",
            "run_id": run_id,
            "timestamp": timestamp,
            "level": level,
            "message": message,
        }
        if transaction_number is not None:
            doc["transaction_number"] = transaction_number
        self._collection.insert_one(doc)
