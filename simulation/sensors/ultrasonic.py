import time
from typing import Callable, Optional
from simulation.gpio_util import gpio

def get_distance_cm(trig_pin: int, echo_pin: int, timeout_s: float = 0.02) -> Optional[float]:
    GPIO = gpio()
    GPIO.setup(trig_pin, GPIO.OUT)
    GPIO.setup(echo_pin, GPIO.IN)

    GPIO.output(trig_pin, False)
    time.sleep(0.0002)
    GPIO.output(trig_pin, True)
    time.sleep(0.00001)
    GPIO.output(trig_pin, False)

    start = time.time()
    while GPIO.input(echo_pin) == 0:
        if time.time() - start > timeout_s:
            return None
    pulse_start = time.time()

    while GPIO.input(echo_pin) == 1:
        if time.time() - pulse_start > timeout_s:
            return None
    pulse_end = time.time()

    distance = ((pulse_end - pulse_start) * 34300.0) / 2.0
    return distance

def run_ultrasonic_loop(trig_pin: int, echo_pin: int, delay: float, callback: Callable[[float, str], None], stop_event):
    while not stop_event.is_set():
        d = get_distance_cm(trig_pin, echo_pin)
        if d is not None:
            callback(d, "DUS1")
        time.sleep(delay)
