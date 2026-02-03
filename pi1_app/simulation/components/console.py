from typing import Any, Optional
from utils.state import SharedState

HELP = """Komande:
  help
  led on|off|toggle|status
  buzzer on|off|beep <ms> <count>|status
  status
  exit
"""

def run_console(led: Any, buzzer: Any, state: SharedState):
    print("\n--- PI1 Console Control ---")
    print(HELP)
    pending = None  # holds a command word awaiting args
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting console...")
            return

        if not line:
            continue

        parts = line.split()
        if pending:
            parts = [pending] + parts
            pending = None

        cmd = parts[0].lower()

        # allow multi-line commands: user can type "led" then on next line "on"
        if cmd in ("led", "buzzer") and len(parts) == 1:
            pending = cmd
            continue

        if cmd in ("exit", "quit"):
            return

        if cmd == "help":
            print(HELP); continue

        if cmd == "status":
            snap = state.snapshot()
            if not snap:
                print("(nema podataka još)")
            else:
                for k, v in snap.items():
                    print(f"{k}: {v}")
            continue

        if cmd == "led":
            if led is None:
                print("LED (DL) nije omogućen u settings.json"); continue
            if len(parts) < 2:
                print("Upotreba: led on|off|toggle|status"); continue
            sub = parts[1].lower()
            if sub == "on": led.on()
            elif sub == "off": led.off()
            elif sub == "toggle": led.toggle()
            elif sub == "status":
                st = getattr(led, "state", None)
                print(f"LED state: {st}")
            else:
                print("Nepoznata opcija. koristi: on/off/toggle/status")
            continue

        if cmd == "buzzer":
            if buzzer is None:
                print("Buzzer (DB) nije omogućen u settings.json"); continue
            if len(parts) < 2:
                print("Upotreba: buzzer on|off|beep <ms> <count>|status"); continue
            sub = parts[1].lower()
            if sub == "on": buzzer.on()
            elif sub == "off": buzzer.off()
            elif sub == "status":
                st = getattr(buzzer, "state", None)
                print(f"Buzzer state: {st}")
            elif sub == "beep":
                ms = int(parts[2]) if len(parts) > 2 else 150
                cnt = int(parts[3]) if len(parts) > 3 else 1
                buzzer.beep(ms, cnt)
            else:
                print("Nepoznata opcija. koristi: on/off/beep/status")
            continue

        print("Nepoznata komanda. Kucaj 'help'.")
