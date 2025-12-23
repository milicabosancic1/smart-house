import time
from simulation.gpio_util import gpio

class Buzzer:
    def __init__(self, pin: int, active_high: bool = True):
        self.pin = pin
        self.active_high = active_high
        self._state = False
        GPIO = gpio()
        GPIO.setup(pin, GPIO.OUT)
        self.off()

    def on(self):
        GPIO = gpio()
        GPIO.output(self.pin, GPIO.HIGH if self.active_high else GPIO.LOW)
        self._state = True

    def off(self):
        GPIO = gpio()
        GPIO.output(self.pin, GPIO.LOW if self.active_high else GPIO.HIGH)
        self._state = False

    def beep(self, ms: int = 200):
        self.on()
        time.sleep(ms / 1000.0)
        self.off()

    @property
    def state(self) -> bool:
        return self._state
