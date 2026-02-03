import time

class SimulatedLed:
    def __init__(self, name: str = "DL"):
        self.name = name
        self._state = False
    def on(self):
        self._state = True
        print(f"[SIM] {self.name} -> ON")
    def off(self):
        self._state = False
        print(f"[SIM] {self.name} -> OFF")
    def toggle(self):
        self.on() if not self._state else self.off()
    @property
    def state(self): return self._state

class SimulatedBuzzer:
    def __init__(self, name: str = "DB"):
        self.name = name
        self._state = False
    def on(self):
        self._state = True
        print(f"[SIM] {self.name} -> ON")
    def off(self):
        self._state = False
        print(f"[SIM] {self.name} -> OFF")
    def beep(self, ms: int = 200):
        print(f"[SIM] {self.name} -> BEEP {ms}ms")
        time.sleep(ms/1000.0)
    @property
    def state(self): return self._state
