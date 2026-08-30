import threading
import time
from datetime import datetime

from paytag_client.api.client import PayTagClient
from paytag_client.api.models import ErrorCode, Item, NeutralizeResult
from paytag_client.domain.basket import Basket
from paytag_client.domain.clock import Clock
from paytag_client.domain.transaction import (
    ItemFinalStatus,
    Transaction,
    TransactionItemRecord,
    TransactionOutcome,
)
from paytag_client.persistence.technical_repo import TechnicalRepository
from paytag_client.persistence.transactions_repo import TransactionRepository


class SessionManager:
    def __init__(
        self,
        api_client: PayTagClient,
        transactions_repo: TransactionRepository,
        technical_repo: TechnicalRepository,
        reporter,
        clock: Clock,
        run_id: str,
        poll_interval_seconds: float,
        neutralize_retry_count: int,
    ):
        self._api = api_client
        self._transactions_repo = transactions_repo
        self._technical_repo = technical_repo
        self._reporter = reporter
        self._clock = clock
        self._run_id = run_id
        self._poll_interval_seconds = poll_interval_seconds
        self._neutralize_retry_count = neutralize_retry_count

        self._transaction: Transaction | None = None
        self._basket: Basket | None = None
        self._stop_polling = threading.Event()
        self._poll_thread: threading.Thread | None = None

    @staticmethod
    def _generate_transaction_number(at: datetime) -> str:
        # Timestamp-based, millisecond precision for collision resistance; also used as the Mongo _id.
        milliseconds = at.microsecond // 1000
        return f"P{at.strftime('%y%m%d%H%M%S')}{milliseconds:03d}"

    def start_session(self) -> None:
        # Session-open guard: a second S while a session is live is business logic, so it lives here
        # rather than in the listener.
        if self._transaction is not None:
            return

        started_at = self._clock.now()
        transaction_number = self._generate_transaction_number(started_at)
        transaction = Transaction(
            transaction_number=transaction_number,
            run_id=self._run_id,
            started_at=started_at,
        )
        self._transactions_repo.insert_started(transaction)

        self._transaction = transaction
        self._basket = Basket()
        self._reporter.session_started(transaction_number)

        self._stop_polling.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        while not self._stop_polling.is_set():
            cycle_start = time.monotonic()

            self._poll_once()

            # Interval measured from cycle start so a slow poll doesn't compound the gap;
            # wait() is both the sleep and the cancellation point when N / Ctrl+C fires.
            elapsed = time.monotonic() - cycle_start
            self._stop_polling.wait(max(0.0, self._poll_interval_seconds - elapsed))

    def _poll_once(self) -> None:
        result = self._api.get_items(self._transaction.transaction_number)
        now = self._clock.now()

        # Branch order is deliberate: success first, then HTTP 400 (our own bug — log it, but the
        # basket on screen is still valid), then any transient fault (keep the stale basket, keep
        # retrying, warn once — never auto-abort; that's the operator's call).
        if result.transport_ok and result.error_code == ErrorCode.NONE:
            self._basket = Basket.from_items(result.items, now)
            self._reporter.basket_updated(self._basket.items)
            return

        if result.http_status == 400:
            self._technical_repo.log_app_event(
                run_id=self._run_id,
                timestamp=now,
                level="error",
                message=f"GetItems returned HTTP 400: {result.error_message}",
                transaction_number=self._transaction.transaction_number,
            )
            return

        self._basket.mark_stale()
        self._technical_repo.log_poll_failure(
            run_id=self._run_id,
            transaction_number=self._transaction.transaction_number,
            timestamp=now,
            endpoint="GetItems",
            error_code=result.error_code,
            error_message=result.error_message,
        )
        self._transactions_repo.record_read_issue(self._transaction.transaction_number, now)
        self._reporter.poll_issue(result.error_message, self._basket.last_confirmed_at)

    def end_session(self) -> None:
        if self._transaction is None:
            return

        self._stop_poll_thread()

        transaction_number = self._transaction.transaction_number
        started_at = self._transaction.started_at
        hard_tag_items = self._basket.hard_tag_items()
        to_neutralize = self._basket.neutralizable_items()

        self._reporter.closing_session(len(self._basket.items), len(hard_tag_items), len(to_neutralize))
        result, attempted_items = self._neutralize_with_retry(transaction_number, to_neutralize)

        # Neutralize is a real, irreversible action and it has already happened by this point.
        # Clear session state now, before persistence — a Mongo failure below must never leave
        # the session "open" and risk a second Neutralize call on already-neutralized items.
        self._transaction = None
        self._basket = None

        item_records = self._build_item_records(hard_tag_items, attempted_items, result)
        outcome = self._build_outcome(result)
        ended_at = self._clock.now()

        self._reporter.session_closed(transaction_number, started_at, ended_at, item_records, outcome)
        self._transactions_repo.mark_closed(transaction_number, ended_at, item_records, outcome)

    def has_open_session(self) -> bool:
        return self._transaction is not None

    def shutdown(self) -> None:
        if self._transaction is not None:
            self._stop_poll_thread()

            transaction_number = self._transaction.transaction_number
            self._transactions_repo.mark_aborted(transaction_number, self._clock.now())
            self._reporter.session_aborted(transaction_number)

            self._transaction = None
            self._basket = None

        self._technical_repo.log_run_ended(self._run_id, self._clock.now())

    def _stop_poll_thread(self) -> None:
        self._stop_polling.set()
        if self._poll_thread is not None:
            self._poll_thread.join()

    def _neutralize_with_retry(
        self, transaction_number: str, items: list[Item]
    ) -> tuple[NeutralizeResult, list[Item]]:
        to_send = items
        result = self._api.neutralize(transaction_number, to_send)
        self._log_neutralize_failure(transaction_number, result)

        for _ in range(self._neutralize_retry_count):
            if result.transport_ok and result.error_code == ErrorCode.NONE:
                break

            next_to_send = self._retry_scope(result, to_send)
            if next_to_send is None:
                break

            to_send = next_to_send
            result = self._api.neutralize(transaction_number, to_send)
            self._log_neutralize_failure(transaction_number, result)

        return result, to_send

    def _log_neutralize_failure(self, transaction_number: str, result: NeutralizeResult) -> None:
        if result.transport_ok and result.error_code == ErrorCode.NONE:
            return

        now = self._clock.now()
        if result.http_status == 400:
            self._technical_repo.log_app_event(
                run_id=self._run_id,
                timestamp=now,
                level="error",
                message=f"Neutralize returned HTTP 400: {result.error_message}",
                transaction_number=transaction_number,
            )
            return

        self._technical_repo.log_poll_failure(
            run_id=self._run_id,
            transaction_number=transaction_number,
            timestamp=now,
            endpoint="Neutralize",
            error_code=result.error_code,
            error_message=result.error_message,
        )

    @staticmethod
    def _retry_scope(result: NeutralizeResult, previously_sent: list[Item]) -> list[Item] | None:
        # Full resend whenever it's unclear what the machine actually touched; a scoped resend of
        # just the failed subset only for code 17, the one response that tells us. None = don't retry.
        if not result.transport_ok:
            return previously_sent

        if result.http_status == 400:
            return None

        if result.error_code == ErrorCode.NOT_ALL_TAGS_NEUTRALIZED:
            return result.failed_items

        return previously_sent

    @staticmethod
    def _records_for(
        items: list[Item], is_hard_tag: bool, status: ItemFinalStatus
    ) -> list[TransactionItemRecord]:
        return [TransactionItemRecord(item.barcode, item.rfid, is_hard_tag, status) for item in items]

    @classmethod
    def _build_item_records(
        cls,
        hard_tag_items: list[Item],
        attempted_items: list[Item],
        result: NeutralizeResult,
    ) -> list[TransactionItemRecord]:
        records = cls._records_for(hard_tag_items, True, ItemFinalStatus.HARD_TAG_PENDING_REMOVAL)

        # Connection lost mid-request: every attempted item is UNCONFIRMED, never assumed neutralized.
        if not result.transport_ok:
            return records + cls._records_for(attempted_items, False, ItemFinalStatus.UNCONFIRMED)

        return (
            records
            + cls._records_for(result.neutralized_items, False, ItemFinalStatus.NEUTRALIZED)
            + cls._records_for(result.failed_items, False, ItemFinalStatus.FAILED)
        )

    @staticmethod
    def _build_outcome(result: NeutralizeResult) -> TransactionOutcome:
        # error_code=None is the "unconfirmed" sentinel — the only case outcome is null on a closed
        # transaction (an aborted one is null because Neutralize never ran).
        if not result.transport_ok:
            return TransactionOutcome(
                error_code=None,
                error_message="Could not confirm neutralization (connection lost during the request)",
            )

        return TransactionOutcome(error_code=result.error_code, error_message=result.error_message)
