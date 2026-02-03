import time
import threading
from typing import Callable, Sequence

from utils.gpio_compat import GPIO


def run_membrane_switch_loop(
    row_pins: Sequence[int],
    col_pins: Sequence[int],
    keymap: Sequence[Sequence[str]],
    poll_s: float,
    callback: Callable[[str, str], None],
    stop_event: threading.Event,
    code: str,
    debounce_ms: int = 200,
) -> None:
    """Matrix keypad scanning (4x4 typical).

    Based on the standard approach shown in lab exercises:
    - Set all row pins LOW
    - Drive one row HIGH at a time and read column inputs
    - If a column reads HIGH, the key at (row, col) is pressed

    Debounce is applied so holding a key does not spam.
    """

    if GPIO is None:
        raise RuntimeError("RPi.GPIO nije dostupan.")

    rows = [int(p) for p in row_pins]
    cols = [int(p) for p in col_pins]

    if len(keymap) != len(rows) or any(len(r) != len(cols) for r in keymap):
        raise ValueError("keymap dimenzije moraju odgovarati row_pins i col_pins")

    # Setup
    for r in rows:
        GPIO.setup(r, GPIO.OUT)
        GPIO.output(r, GPIO.LOW)

    for c in cols:
        GPIO.setup(c, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    last_key = None
    last_ts = 0.0

    def emit(key: str):
        nonlocal last_key, last_ts
        now = time.time()
        if key == last_key and (now - last_ts) * 1000.0 < float(debounce_ms):
            return
        last_key = key
        last_ts = now
        callback(key, code)

    while not stop_event.is_set():
        for ri, rpin in enumerate(rows):
            GPIO.output(rpin, GPIO.HIGH)
            # Small settle time
            time.sleep(0.0008)
            for ci, cpin in enumerate(cols):
                if GPIO.input(cpin) == GPIO.HIGH:
                    emit(str(keymap[ri][ci]))
            GPIO.output(rpin, GPIO.LOW)
        time.sleep(float(poll_s))
