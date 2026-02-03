from typing import Dict, Any
import time

from gpio_util import has_gpio
from actuators.simulated import SimulatedLed, SimulatedBuzzer

HELP = """Komande (CLI za aktuatora):
  dlon                -> upali svetlo (DL)
  dlof                -> ugasi svetlo (DL)
  dltog               -> toggle svetlo (DL)

  dbon                -> uključi buzzer (DB)
  dboff               -> isključi buzzer (DB)
  dbbip <n> [ms]      -> uradi n bip-ova (podrazumevano ms=200)

  status              -> prikaži trenutno stanje
  help                -> ova pomoć
  exit                -> izlaz
"""

def create_led(cfg: Dict[str, Any]):
    if cfg.get("simulated", True) or not has_gpio():
        return SimulatedLed("DL")
    from actuators.led import Led
    return Led(cfg["pin"], active_high=cfg.get("active_high", True))

def create_buzzer(cfg: Dict[str, Any]):
    if cfg.get("simulated", True) or not has_gpio():
        return SimulatedBuzzer("DB")
    from actuators.buzzer import Buzzer
    return Buzzer(cfg["pin"], active_high=cfg.get("active_high", True))

def run_console(settings: Dict[str, Any], stop_event):
    led = create_led(settings.get("DL", {}))
    buzzer = create_buzzer(settings.get("DB", {}))

    print(HELP)
    while not stop_event.is_set():
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in ("exit", "quit"):
            break

        if cmd == "help":
            print(HELP)
            continue

        if cmd == "status":
            print(f"DL={'ON' if led.state else 'OFF'} | DB={'ON' if buzzer.state else 'OFF'}")
            continue

        # === Svetlo (DL) ===
        if cmd == "dlon":
            led.on()
            print("[OK] DL uključen.")
            continue
        if cmd == "dlof":
            led.off()
            print("[OK] DL isključen.")
            continue
        if cmd == "dltog":
            led.toggle()
            print(f"[OK] DL -> {'ON' if led.state else 'OFF'}.")
            continue

        # === Buzzer (DB) ===
        if cmd == "dbon":
            buzzer.on()
            print("[OK] DB uključen.")
            continue
        if cmd == "dboff":
            buzzer.off()
            print("[OK] DB isključen.")
            continue

        if cmd == "dbbip":
            if len(parts) < 2:
                print("Upotreba: dbbip <n> [ms]")
                continue
            try:
                n = int(parts[1])
                ms = int(parts[2]) if len(parts) >= 3 else 200
            except ValueError:
                print("Greška: n i ms moraju biti brojevi. Primer: dbbip 3 250")
                continue

            n = max(1, min(50, n))  # neka razumna granica
            ms = max(10, min(5000, ms))

            for i in range(n):
                buzzer.beep(ms)
                # kratka pauza između bip-ova (da se jasno čuje/vidi)
                if i != n - 1:
                    time.sleep(0.08)

            print(f"[OK] DB odradio {n} bip-a ({ms}ms).")
            continue

        print("Nepoznata komanda. Kucaj 'help'.")
