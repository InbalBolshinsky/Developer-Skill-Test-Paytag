from paytag_client.api.models import ErrorCode, Item, NeutralizeResult
from paytag_client.domain.session import SessionManager

SENT = [Item(barcode="1", rfid="R1", is_hard_tag=False), Item(barcode="2", rfid="R2", is_hard_tag=False)]
FAILED_SUBSET = [Item(barcode="2", rfid="R2", is_hard_tag=False)]


def _result(**overrides) -> NeutralizeResult:
    defaults = dict(
        transport_ok=True,
        http_status=200,
        error_code=ErrorCode.NONE,
        error_message=None,
        neutralized_items=[],
        failed_items=[],
    )
    defaults.update(overrides)
    return NeutralizeResult(**defaults)


def test_connection_failure_triggers_a_full_resend():
    result = _result(transport_ok=False, http_status=None, error_code=None)

    assert SessionManager._retry_scope(result, SENT) == SENT


def test_http_400_is_never_retried():
    result = _result(http_status=400, error_code=ErrorCode.GENERAL_ERROR, error_message="TransactionNumber is required")

    assert SessionManager._retry_scope(result, SENT) is None


def test_not_all_tags_neutralized_retries_only_the_failed_subset():
    result = _result(
        error_code=ErrorCode.NOT_ALL_TAGS_NEUTRALIZED,
        neutralized_items=[SENT[0]],
        failed_items=FAILED_SUBSET,
    )

    assert SessionManager._retry_scope(result, SENT) == FAILED_SUBSET


def test_general_error_falls_back_to_a_full_resend():
    result = _result(error_code=ErrorCode.GENERAL_ERROR)

    assert SessionManager._retry_scope(result, SENT) == SENT


def test_reader_not_connected_falls_back_to_a_full_resend():
    result = _result(error_code=ErrorCode.READER_NOT_CONNECTED)

    assert SessionManager._retry_scope(result, SENT) == SENT


def test_neutralizer_not_connected_falls_back_to_a_full_resend():
    result = _result(error_code=ErrorCode.NEUTRALIZER_NOT_CONNECTED)

    assert SessionManager._retry_scope(result, SENT) == SENT


def test_an_undemonstrated_hardware_code_still_falls_back_to_a_full_resend():
    # Codes 2/3/5-16 were never demonstrated by PayTag's own examples - the design
    # treats anything not explicitly handled as "unsure what was touched," full resend.
    result = _result(error_code=ErrorCode.HARDWARE_GENERAL_ERROR)

    assert SessionManager._retry_scope(result, SENT) == SENT
