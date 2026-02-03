import time
from typing import Callable
from simulation.gpio_util import gpio

def run_pir_loop(pin: int, delay: float, callback: Callable[[bool, str], None], stop_event):
    """Poll a PIR motion sensor (HIGH = motion)."""
    GPIO = gpio()
    GPIO.setup(pin, GPIO.IN)
    last = GPIO.input(pin)
    while not stop_event.is_set():
        v = GPIO.input(pin)
        if v != last:
            callback(v == GPIO.HIGH, "DPIR1")
            last = v
        time.sleep(delay)
