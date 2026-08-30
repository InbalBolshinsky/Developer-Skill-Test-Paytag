from typing import Callable

from pynput import keyboard


class HotkeyListener:
    def __init__(
        self,
        scan_key: str,
        neutralize_key: str,
        on_scan: Callable[[], None],
        on_neutralize: Callable[[], None],
    ):
        self._scan_key = scan_key.lower()
        self._neutralize_key = neutralize_key.lower()
        self._on_scan = on_scan
        self._on_neutralize = on_neutralize
        self._listener: keyboard.Listener | None = None

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._handle_press)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def _handle_press(self, key) -> None:
        pressed = self._char_for(key)
        if pressed is None:
            return

        if pressed == self._scan_key:
            self._on_scan()
        elif pressed == self._neutralize_key:
            self._on_neutralize()

    @staticmethod
    def _char_for(key) -> str | None:
        char = getattr(key, "char", None)
        return char.lower() if char is not None else None
