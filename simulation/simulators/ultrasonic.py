import time
import math
import random
from typing import Callable, Optional, Dict, Any

def run_ultrasonic_simulator(delay: float,
                            callback: Callable[[float, str], None],
                            stop_event,
                            code: str = "DUS1",
                            sim_cfg: Optional[Dict[str, Any]] = None):
    """
    Simulacija udaljenosti kao sinusoida (sa opcionalnim šumom).

    sim_cfg (opciono):
      - mean: srednja vrednost (cm)
      - amp: amplituda (cm)
      - period: period (sekunde)
      - noise: standardna devijacija Gauss šuma (cm)
      - min: donja granica (cm)
      - max: gornja granica (cm)
    """
    sim_cfg = sim_cfg or {}
    mean = float(sim_cfg.get("mean", 120.0))
    amp = float(sim_cfg.get("amp", 60.0))
    period = float(sim_cfg.get("period", 10.0))
    noise = float(sim_cfg.get("noise", 0.0))
    min_d = float(sim_cfg.get("min", 5.0))
    max_d = float(sim_cfg.get("max", 250.0))

    t0 = time.monotonic()
    while not stop_event.is_set():
        t = time.monotonic() - t0
        # sinusoida: mean + amp*sin(2πt/period)
        val = mean + amp * math.sin(2.0 * math.pi * (t / max(0.001, period)))
        if noise > 0:
            val += random.gauss(0.0, noise)
        val = max(min_d, min(max_d, val))
        callback(val, code)
        time.sleep(delay)
