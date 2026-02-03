import time
import random
from typing import Callable, List, Optional

def run_dms_simulator(delay: float,
                      callback: Callable[[str, str], None],
                      stop_event,
                      code: str = "DMS1",
                      keys: Optional[List[str]] = None):
    """
    Simulacija DMS (membrane switch / keypad) – periodično emituje "pritisnuti taster".

    - delay: period (sekunde) između emitovanja događaja
    - keys: lista dozvoljenih tastera (default: 4x4 keypad)
    """
    if keys is None or len(keys) == 0:
        keys = ["1","2","3","A","4","5","6","B","7","8","9","C","*","0","#","D"]

    while not stop_event.is_set():
        key = random.choice(keys)
        callback(str(key), code)
        time.sleep(delay)
