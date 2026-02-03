import threading
import time

from settings import load_settings

from components.pi1_devices import start_pi1_sensors
from console_app import run_console

try:
    import RPi.GPIO as GPIO  # type: ignore
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
except Exception:
    GPIO = None  # type: ignore

if __name__ == "__main__":
    print("Starting PI1 app (Kontrolna tačka 1)")
    settings = load_settings()

    threads = []
    stop_event = threading.Event()

    # start sensors (each prints to console via callbacks)
    start_pi1_sensors(settings, threads, stop_event)

    # run console commands in main thread
    try:
        run_console(settings, stop_event)
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=1.0)
        if GPIO is not None:
            try:
                GPIO.cleanup()
            except Exception:
                pass
        print("Stopped.")
