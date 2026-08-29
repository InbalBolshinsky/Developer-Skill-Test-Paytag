import requests

from paytag_client.api.models import (
    ErrorCode,
    GetItemsResult,
    HealthStatus,
    Item,
    NeutralizeResult,
)


class PayTagClient:
    def __init__(self, base_url: str, request_timeout_seconds: float):
        self._base_url = base_url
        self._timeout = request_timeout_seconds

    def get_health(self) -> HealthStatus | None:
        try:
            response = requests.get(f"{self._base_url}/info", timeout=self._timeout)
        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None

        body = response.json()
        machine_status = body["machine_status"]
        return HealthStatus(
            version=body["version"],
            reader_connected=machine_status["reader_status"],
            neutralizer_connected=machine_status["neutralizer_status"],
            all_connected=machine_status["all_connected"],
        )

    def get_items(self, transaction_number: str) -> GetItemsResult:
        try:
            response = requests.post(
                f"{self._base_url}/partner/GetItems",
                json={"TransactionNumber": transaction_number},
                timeout=self._timeout,
            )
        except requests.RequestException:
            return GetItemsResult(
                transport_ok=False,
                http_status=None,
                error_code=None,
                error_message=None,
                items=[],
            )

        body = response.json()
        return GetItemsResult(
            transport_ok=True,
            http_status=response.status_code,
            error_code=ErrorCode(body["ErrorCode"]),
            error_message=body["ErrorMessage"],
            items=[Item.from_dict(i) for i in body["Items"]],
        )

    def neutralize(self, transaction_number: str, items: list[Item]) -> NeutralizeResult:
        try:
            response = requests.post(
                f"{self._base_url}/partner/Neutralize",
                json={
                    "TransactionNumber": transaction_number,
                    "Items": [{"Barcode": i.barcode, "RFID": i.rfid} for i in items],
                },
                timeout=self._timeout,
            )
        except requests.RequestException:
            return NeutralizeResult(
                transport_ok=False,
                http_status=None,
                error_code=None,
                error_message=None,
                neutralized_items=[],
                failed_items=[],
            )

        body = response.json()
        return NeutralizeResult(
            transport_ok=True,
            http_status=response.status_code,
            error_code=ErrorCode(body["ErrorCode"]),
            error_message=body["ErrorMessage"],
            neutralized_items=[Item.from_dict(i) for i in body["NeutralizedRFItems"]],
            failed_items=[Item.from_dict(i) for i in body["FailedRFItems"]],
        )
