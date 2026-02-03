import random, time
from typing import Callable
import threading

def run_pir_simulator(poll_s: float, callback: Callable[[bool, str], None], stop_event: threading.Event, code: str):
    """Simulira PIR: 'motion' se pojavi na kratko."""
    motion = False
    while not stop_event.is_set():
        if not motion and random.random() < 0.15:
            motion = True
            callback(True, code)
        elif motion and random.random() < 0.4:
            motion = False
            callback(False, code)
        time.sleep(poll_s)
