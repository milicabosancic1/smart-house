import time
import random
from typing import Callable

def run_button_simulator(delay: float, callback: Callable[[bool, str], None], stop_event, code: str = "DS1"):
    """Random press/release events."""
    pressed = False
    while not stop_event.is_set():
        # 15% chance to toggle state each tick
        if random.random() < 0.15:
            pressed = not pressed
            callback(pressed, code)
        time.sleep(delay)
