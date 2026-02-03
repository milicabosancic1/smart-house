from dataclasses import dataclass

@dataclass
class SimLed:
    state: bool = False
    def setup(self): ...
    def on(self): self.state = True; print("[DL] LED -> ON")
    def off(self): self.state = False; print("[DL] LED -> OFF")
    def toggle(self): self.state = not self.state; print(f"[DL] LED -> {'ON' if self.state else 'OFF'}")

@dataclass
class SimBuzzer:
    state: bool = False
    def setup(self): ...
    def on(self): self.state = True; print("[DB] BUZZER -> ON")
    def off(self): self.state = False; print("[DB] BUZZER -> OFF")
    def beep(self, ms: int = 150, count: int = 1, gap_ms: int = 120):
        print(f"[DB] BUZZER -> BEEP ms={ms} count={count} gap_ms={gap_ms}")
