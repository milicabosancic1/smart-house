import time
import threading
from typing import Callable, Optional

from utils.gpio_compat import GPIO


class PirSensor:
    """PIR motion sensor."""

    def __init__(self, pin: int, pull: Optional[str] = None):
        self.pin = int(pin)
        self.pull = (pull or "").upper().strip()

    def setup(self) -> None:
        if GPIO is None:
            raise RuntimeError("RPi.GPIO nije dostupan (pokrećeš na PC-u?).")

        if self.pull == "UP":
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        elif self.pull == "DOWN":
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        else:
            GPIO.setup(self.pin, GPIO.IN)

    def read_motion(self) -> bool:
        if GPIO is None:
            return False
        return GPIO.input(self.pin) == GPIO.HIGH


def run_pir(
    sensor: PirSensor,
    poll_s: float,
    callback: Callable[[bool, str], None],
    stop_event: threading.Event,
    code: str,
    *,
    use_events: bool = True,
) -> None:
    """Runs PIR loop.

    If GPIO is available and use_events=True, uses edge detection.
    Otherwise falls back to polling.
    """
    sensor.setup()

    last = sensor.read_motion()
    callback(last, code)

    if GPIO is None or not use_events:
        while not stop_event.is_set():
            cur = sensor.read_motion()
            if cur != last:
                last = cur
                callback(cur, code)
            time.sleep(poll_s)
        return

    def _gpio_cb(_channel: int) -> None:
        nonlocal last
        cur = sensor.read_motion()
        if cur != last:
            last = cur
            callback(cur, code)

    try:
        GPIO.add_event_detect(sensor.pin, GPIO.BOTH, callback=_gpio_cb)
        while not stop_event.is_set():
            time.sleep(0.1)
    finally:
        try:
            GPIO.remove_event_detect(sensor.pin)
        except Exception:
            pass
