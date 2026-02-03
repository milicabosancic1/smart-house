from utils.gpio_compat import GPIO

class LedActuator:
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

    def toggle(self):
        if self._state:
            self.off()
        else:
            self.on()

    @property
    def state(self) -> bool:
        return self._state
