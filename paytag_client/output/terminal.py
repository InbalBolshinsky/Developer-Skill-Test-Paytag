from datetime import datetime

from paytag_client.api.models import Item
from paytag_client.domain.clock import Clock
from paytag_client.domain.transaction import ItemFinalStatus, TransactionItemRecord, TransactionOutcome


class TerminalReporter:
    def __init__(self, clock: Clock):
        self._clock = clock
        self._known_rfids: set[str] = set()
        self._issue_active = False

    def _log(self, message: str) -> None:
        timestamp = self._clock.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def session_started(self, transaction_number: str) -> None:
        self._known_rfids = set()
        self._issue_active = False
        self._log(f"Session {transaction_number} started — scanning...")

    def poll_issue(self, error_message: str | None, basket_as_of: datetime | None) -> None:
        if self._issue_active:
            return
        self._issue_active = True

        reason = error_message or "connection issue"
        as_of = basket_as_of.strftime("%H:%M:%S") if basket_as_of else "unknown"
        self._log(f"⚠ Could not read the scanner ({reason}) — showing basket as of {as_of}, retrying...")

    def basket_updated(self, items: list[Item]) -> None:
        current_rfids = {item.rfid for item in items}
        new_items = [item for item in items if item.rfid not in self._known_rfids]

        if self._issue_active:
            self._issue_active = False
            if current_rfids == self._known_rfids:
                self._log("✓ Scanner back online — basket confirmed, no changes")
                return
            self._log("✓ Scanner back online")

        if not new_items:
            self._known_rfids = current_rfids
            return

        for item in new_items:
            tag_note = " — HARD TAG" if item.is_hard_tag else ""
            masked_rfid = f"{item.rfid[:8]}...{item.rfid[-4:]}"
            self._log(f"  + Item added: barcode {item.barcode} (RFID {masked_rfid}){tag_note}")

        self._known_rfids = current_rfids
        hard_tag_count = sum(1 for item in items if item.is_hard_tag)
        hard_tag_note = f" ({hard_tag_count} hard tag{'s' if hard_tag_count != 1 else ''})" if hard_tag_count else ""
        self._log(f"Basket now has {len(items)} items{hard_tag_note}")

    def closing_session(self, total_items: int, hard_tag_count: int, neutralize_count: int) -> None:
        if hard_tag_count:
            tag_word = "tag" if hard_tag_count == 1 else "tags"
            hard_tag_note = f" ({hard_tag_count} hard {tag_word} excluded from neutralization)"
        else:
            hard_tag_note = ""
        self._log(f"Closing session — finalizing basket: {total_items} items{hard_tag_note}")

        item_word = "item" if neutralize_count == 1 else "items"
        self._log(f"Neutralizing {neutralize_count} {item_word}...")

    def session_closed(
        self,
        transaction_number: str,
        started_at: datetime,
        ended_at: datetime,
        item_records: list[TransactionItemRecord],
        outcome: TransactionOutcome,
    ) -> None:
        if outcome.error_code is None:
            self._print_action_required(ended_at, outcome.error_message)
        else:
            self._print_checkout_result(transaction_number, started_at, ended_at, item_records)

        self._log("Ready. Press S to start a checkout session, Ctrl+C to exit.")

    def session_aborted(self, transaction_number: str) -> None:
        self._log(f"Shutting down — session {transaction_number} marked as aborted")

    @staticmethod
    def _print_action_required(ended_at: datetime, error_message: str | None) -> None:
        timestamp = ended_at.strftime("%H:%M:%S")
        print()
        print(" ACTION REQUIRED ".center(77, "="))
        print(f" {timestamp} — {error_message}")
        print(" DO NOT assume items are neutralized. Check the gate/machine manually.")
        print("=" * 77)
        print()

    @staticmethod
    def _print_checkout_result(
        transaction_number: str,
        started_at: datetime,
        ended_at: datetime,
        item_records: list[TransactionItemRecord],
    ) -> None:
        duration = int((ended_at - started_at).total_seconds())
        neutralized = [r for r in item_records if r.final_status == ItemFinalStatus.NEUTRALIZED]
        failed = [r for r in item_records if r.final_status == ItemFinalStatus.FAILED]
        hard_tags = [r for r in item_records if r.final_status == ItemFinalStatus.HARD_TAG_PENDING_REMOVAL]

        print()
        print(f" CHECKOUT RESULT — {transaction_number} ".center(77, "="))
        print(f" Closed at {ended_at.strftime('%H:%M:%S')} (session lasted {duration}s)")
        print()
        print(f" ✓ Neutralized:                {len(neutralized)} item{'s' if len(neutralized) != 1 else ''}")
        print(f" ✗ Failed:                     {len(failed)} item{'s' if len(failed) != 1 else ''}")
        if hard_tags:
            barcodes = ", ".join(f"barcode {r.barcode}" for r in hard_tags)
            plural = "s" if len(hard_tags) != 1 else ""
            print(f" ⚠ HARD TAG — REMOVE MANUALLY: {len(hard_tags)} item{plural} ({barcodes})")
        print("=" * 77)
        print()
