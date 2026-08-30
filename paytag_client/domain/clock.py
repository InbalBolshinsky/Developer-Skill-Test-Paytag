from datetime import datetime


# Thin wrapper over the system clock so tests can inject a deterministic time source.
class Clock:
    def now(self) -> datetime:
        return datetime.now()
