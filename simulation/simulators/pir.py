import time
import random
from typing import Callable

def run_pir_simulator(delay: float, callback: Callable[[bool, str], None], stop_event, code: str = "DPIR1"):
    motion = False
    while not stop_event.is_set():
        # motion bursts
        if random.random() < 0.10:
            motion = True
        elif random.random() < 0.30:
            motion = False
        callback(motion, code)
        time.sleep(delay)
