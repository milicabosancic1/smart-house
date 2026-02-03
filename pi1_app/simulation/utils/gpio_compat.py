"""GPIO compatibility layer.

- Raspberry Pi: uses RPi.GPIO with BCM numbering
- Non-Pi: GPIO is None so the app can run in simulation

This module is intentionally safe to import even when RPi.GPIO is missing.
"""

from __future__ import annotations

from typing import Optional

GPIO = None  # type: ignore

try:
    import RPi.GPIO as _GPIO  # type: ignore

    _GPIO.setwarnings(False)
    _GPIO.setmode(_GPIO.BCM)
    GPIO = _GPIO  # type: ignore
except Exception:
    GPIO = None  # type: ignore


def available() -> bool:
    return GPIO is not None


def cleanup() -> None:
    """Cleanup GPIO state (safe to call multiple times)."""
    if GPIO is None:
        return
    try:
        GPIO.cleanup()
    except Exception:
        pass
