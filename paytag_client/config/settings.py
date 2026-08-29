from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class Settings:
    machine_base_url: str
    machine_request_timeout_seconds: float
    poll_interval_seconds: float
    neutralize_retry_count: int
    scan_hotkey: str
    neutralize_hotkey: str
    mongo_uri: str
    mongo_db_name: str


def load_settings(path: str) -> Settings:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    return Settings(
        machine_base_url=raw["machine"]["base_url"],
        machine_request_timeout_seconds=raw["machine"]["request_timeout_seconds"],
        poll_interval_seconds=raw["session"]["poll_interval_seconds"],
        neutralize_retry_count=raw["session"]["neutralize_retry_count"],
        scan_hotkey=raw["hotkeys"]["scan"],
        neutralize_hotkey=raw["hotkeys"]["neutralize"],
        mongo_uri=raw["mongo"]["uri"],
        mongo_db_name=raw["mongo"]["db_name"],
    )
