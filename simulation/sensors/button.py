import time
from typing import Callable
from simulation.gpio_util import gpio

def run_button_loop(pin: int, delay: float, callback: Callable[[bool, str], None], stop_event, pull_up: bool = True):
    """Poll a GPIO button and report state changes."""
    GPIO = gpio()
    pud = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
    GPIO.setup(pin, GPIO.IN, pull_up_down=pud)
    last = GPIO.input(pin)
    while not stop_event.is_set():
        v = GPIO.input(pin)
        if v != last:
            pressed = (v == GPIO.LOW) if pull_up else (v == GPIO.HIGH)
            callback(pressed, "DS1")
            last = v
        time.sleep(delay)
