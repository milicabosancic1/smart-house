import random, time
from typing import Callable
import threading

def run_ultrasonic_simulator(poll_s: float, callback: Callable[[float, str], None], stop_event: threading.Event, code: str):
    """Simulira udaljenost u cm."""
    while not stop_event.is_set():
        dist = round(random.uniform(5.0, 200.0), 1)
        callback(dist, code)
        time.sleep(poll_s)
