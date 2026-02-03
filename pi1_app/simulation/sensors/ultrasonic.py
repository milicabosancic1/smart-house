import time, threading
from typing import Callable
from utils.gpio_compat import GPIO

class UltrasonicSensor:
    def __init__(self, trigger_pin: int, echo_pin: int):
        self.trig = int(trigger_pin)
        self.echo = int(echo_pin)

    def setup(self):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO nije dostupan.")
        GPIO.setup(self.trig, GPIO.OUT)
        GPIO.setup(self.echo, GPIO.IN)
        GPIO.output(self.trig, GPIO.LOW)
        time.sleep(0.05)

    def measure_cm(self, timeout_s: float = 0.03) -> float:
        if GPIO is None:
            return 0.0

        GPIO.output(self.trig, GPIO.HIGH)
        time.sleep(0.00001)  # 10us
        GPIO.output(self.trig, GPIO.LOW)

        start = time.time()
        while GPIO.input(self.echo) == GPIO.LOW:
            if time.time() - start > timeout_s:
                return float("inf")
        pulse_start = time.time()

        while GPIO.input(self.echo) == GPIO.HIGH:
            if time.time() - pulse_start > timeout_s:
                return float("inf")
        pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        # brzina zvuka ~34300 cm/s, put je tamo+nazad
        dist_cm = (pulse_duration * 34300) / 2
        return dist_cm

def run_ultrasonic_loop(sensor: UltrasonicSensor, poll_s: float, callback: Callable[[float, str], None], stop_event: threading.Event, code: str):
    sensor.setup()
    while not stop_event.is_set():
        dist = sensor.measure_cm()
        callback(round(dist, 1) if dist != float("inf") else dist, code)
        time.sleep(poll_s)
