import time
import threading
from typing import Callable, Optional

from utils.gpio_compat import GPIO


class ButtonSensor:
    """GPIO button sensor.

    Default wiring (recommended):
      - Button between BCM pin and GND
      - Internal pull-up enabled (PUD_UP)

    In that case, the raw pin reads LOW when pressed.
    """

    def __init__(self, pin: int, pull: str = "UP", invert: Optional[bool] = None):
        self.pin = int(pin)
        self.pull = (pull or "UP").upper()

        # If not explicitly provided, assume active-low when using pull-up
        if invert is None:
            self.invert = (self.pull == "UP")
        else:
            self.invert = bool(invert)

    def setup(self) -> None:
        if GPIO is None:
            raise RuntimeError("RPi.GPIO nije dostupan (pokrećeš na PC-u?).")
        pud = GPIO.PUD_UP if self.pull == "UP" else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)

    def read_pressed(self) -> bool:
        if GPIO is None:
            return False
        raw = GPIO.input(self.pin)
        pressed = (raw == GPIO.HIGH)
        return (not pressed) if self.invert else pressed


def run_button(
    sensor: ButtonSensor,
    poll_s: float,
    callback: Callable[[bool, str], None],
    stop_event: threading.Event,
    code: str,
    *,
    use_events: bool = True,
    bouncetime_ms: int = 150,
) -> None:
    """Runs button loop.

    If GPIO is available and use_events=True, uses edge detection.
    Otherwise falls back to polling.
    """
    sensor.setup()

    # initial state
    last = sensor.read_pressed()
    callback(last, code)

    if GPIO is None or not use_events:
        # Polling fallback
        while not stop_event.is_set():
            cur = sensor.read_pressed()
            if cur != last:
                last = cur
                callback(cur, code)
            time.sleep(poll_s)
        return

    # Edge-detect mode
    def _gpio_cb(_channel: int) -> None:
        nonlocal last
        cur = sensor.read_pressed()
        if cur != last:
            last = cur
            callback(cur, code)

    try:
        GPIO.add_event_detect(sensor.pin, GPIO.BOTH, callback=_gpio_cb, bouncetime=int(bouncetime_ms))
        while not stop_event.is_set():
            time.sleep(0.1)
    finally:
        try:
            GPIO.remove_event_detect(sensor.pin)
        except Exception:
            pass
