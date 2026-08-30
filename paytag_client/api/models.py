from dataclasses import dataclass
from enum import IntEnum


class ErrorCode(IntEnum):
    NONE = 0
    GENERAL_ERROR = 1
    HARDWARE_GENERAL_ERROR = 2
    HARDWARE_REQUEST_TIMEOUT = 3
    READER_NOT_CONNECTED = 4
    TAG_READ_ERROR = 5
    READER_BUSY = 6
    LOW_SIGNAL_STRENGTH = 7
    NEUTRALIZER_NOT_CONNECTED = 8
    HARD_TAG_RELEASE_ERROR = 9
    COMMUNICATION_ERROR = 10
    INVALID_RESPONSE = 11
    COMMAND_TIMEOUT = 12
    DATA_CORRUPTION = 13
    COMMUNICATION_RESET = 14
    SECURITY_VIOLATION = 15
    CONFIGURATION_ERROR = 16
    NOT_ALL_TAGS_NEUTRALIZED = 17


@dataclass(frozen=True)
class Item:
    barcode: str
    rfid: str
    is_hard_tag: bool

    @staticmethod
    def from_dict(d: dict) -> "Item":
        # Pick only known fields on purpose: a firmware update adding fields must not break parsing.
        return Item(
            barcode=d["Barcode"],
            rfid=d["RFID"],
            is_hard_tag=d["IsHardTag"],
        )


@dataclass(frozen=True)
class HealthStatus:
    version: str
    reader_connected: bool
    neutralizer_connected: bool
    all_connected: bool


# Three-channel API outcome: transport_ok (did we get a response), http_status, and the
# application ErrorCode. Every caller checks all three rather than trusting the JSON body alone.
@dataclass(frozen=True)
class GetItemsResult:
    transport_ok: bool
    http_status: int | None
    error_code: ErrorCode | None
    error_message: str | None
    items: list[Item]


@dataclass(frozen=True)
class NeutralizeResult:
    transport_ok: bool
    http_status: int | None
    error_code: ErrorCode | None
    error_message: str | None
    neutralized_items: list[Item]
    failed_items: list[Item]
