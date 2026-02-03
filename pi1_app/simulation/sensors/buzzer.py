import time
from utils.gpio_compat import GPIO

class BuzzerActuator:
    def __init__(self, pin: int):
        self.pin = int(pin)
        self._state = False

    def setup(self):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO nije dostupan.")
        GPIO.setup(self.pin, GPIO.OUT)
        self.off()

    def on(self):
        self._state = True
        if GPIO is not None:
            GPIO.output(self.pin, GPIO.HIGH)

    def off(self):
        self._state = False
        if GPIO is not None:
            GPIO.output(self.pin, GPIO.LOW)

    def beep(self, ms: int = 150, count: int = 1, gap_ms: int = 120):
        for _ in range(max(1, int(count))):
            self.on()
            time.sleep(max(1, int(ms)) / 1000.0)
            self.off()
            time.sleep(max(0, int(gap_ms)) / 1000.0)

    @property
    def state(self) -> bool:
        return self._state
