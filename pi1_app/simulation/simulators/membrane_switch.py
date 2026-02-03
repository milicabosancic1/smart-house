import random, time
from typing import Callable, List
import threading

def run_membrane_switch_simulator(poll_s: float, keys: List[str], callback: Callable[[str, str], None], stop_event: threading.Event, code: str):
    """Simulira pritiske tastera na membranskoj tastaturi."""
    while not stop_event.is_set():
        if random.random() < 0.35:
            key = random.choice(keys or ["1","2","3"])
            callback(key, code)
        time.sleep(poll_s)

# Backwards-compatible alias expected by components
run_membrane_simulator = run_membrane_switch_simulator

