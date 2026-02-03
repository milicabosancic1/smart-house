"""GPIO helper: gracefully handles running on non-RPi machines."""
try:
    import RPi.GPIO as GPIO  # type: ignore
    _HAS_GPIO = True
except Exception:
    GPIO = None  # type: ignore
    _HAS_GPIO = False

def has_gpio() -> bool:
    return _HAS_GPIO

def gpio():
    if not _HAS_GPIO:
        raise RuntimeError("RPi.GPIO not available (running in simulation/non-RPi environment).")
    return GPIO
