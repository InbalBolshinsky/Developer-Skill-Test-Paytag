import signal
import sys
import threading
import uuid

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from paytag_client.api.client import PayTagClient
from paytag_client.config.settings import load_settings
from paytag_client.domain.clock import Clock
from paytag_client.domain.session import SessionManager
from paytag_client.hotkeys.listener import HotkeyListener
from paytag_client.output.terminal import TerminalReporter
from paytag_client.persistence.technical_repo import TechnicalRepository
from paytag_client.persistence.transactions_repo import TransactionRepository


def main() -> None:
    settings = load_settings("config.yaml")
    clock = Clock()
    reporter = TerminalReporter(clock)

    reporter.startup()
    reporter.config_loaded()

    api_client = PayTagClient(settings.machine_base_url, settings.machine_request_timeout_seconds)

    health = api_client.get_health()
    reporter.report_machine_check(settings.machine_base_url, health)
    if health is None:
        sys.exit(1)

    try:
        mongo_client = MongoClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=int(settings.mongo_server_selection_timeout_seconds * 1000),
        )
        database = mongo_client[settings.mongo_db_name]
        transactions_repo = TransactionRepository(database["transactions"])
        technical_repo = TechnicalRepository(database["technical"])
    except PyMongoError:
        reporter.mongo_unreachable()
        sys.exit(1)

    run_id = str(uuid.uuid4())
    technical_repo.log_run_started(run_id, clock.now())
    technical_repo.log_health_check(run_id, clock.now(), health)

    session_manager = SessionManager(
        api_client=api_client,
        transactions_repo=transactions_repo,
        technical_repo=technical_repo,
        reporter=reporter,
        clock=clock,
        run_id=run_id,
        poll_interval_seconds=settings.poll_interval_seconds,
        neutralize_retry_count=settings.neutralize_retry_count,
    )

    listener = HotkeyListener(
        scan_key=settings.scan_hotkey,
        neutralize_key=settings.neutralize_hotkey,
        on_scan=session_manager.start_session,
        on_neutralize=session_manager.end_session,
    )
    listener.start()

    reporter.ready()

    shutdown_requested = threading.Event()
    signal.signal(signal.SIGINT, lambda signum, frame: shutdown_requested.set())
    shutdown_requested.wait()

    listener.stop()
    was_open = session_manager.has_open_session()
    session_manager.shutdown()
    if not was_open:
        reporter.shutting_down_idle()
    reporter.goodbye()


if __name__ == "__main__":
    main()
