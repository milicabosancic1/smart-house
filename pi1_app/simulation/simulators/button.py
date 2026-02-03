import random, time
from typing import Callable
import threading

def run_button_simulator(poll_s: float, callback: Callable[[bool, str], None], stop_event: threading.Event, code: str):
    """Simulira door button: povremeno generiše 'pressed' događaj."""
    pressed = False
    while not stop_event.is_set():
        # Sa malom verovatnoćom promeni stanje (kao pritiskanje)
        if random.random() < 0.08:
            pressed = not pressed
            callback(pressed, code)
        time.sleep(poll_s)
