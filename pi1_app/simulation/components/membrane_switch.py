import threading
from typing import Optional

from utils.printing import banner
from utils.state import SharedState
from utils.device_payload import build_payload

from simulators.membrane_switch import run_membrane_simulator


def dms_callback(
    key: str,
    code: str,
    device_name: str,
    simulated: bool,
    topic: Optional[str],
    pi_id: str,
    batch_sender,
    state: SharedState,
):
    banner(code)
    print(f"Key: {key}")
    state.set(code, {"key": key})

    if batch_sender is not None and topic:
        payload = build_payload(pi_id, code, device_name, key, simulated, extra={"kind": "membrane"})
        batch_sender.enqueue(topic, payload)


def run_dms(
    settings: dict,
    threads: list,
    stop_event: threading.Event,
    state: SharedState,
    pi_id: str = "PI1",
    batch_sender=None,
):
    if not settings.get("enabled", True):
        return

    code = "DMS"
    poll_s = float(settings.get("poll_s", 0.15))
    simulated = bool(settings.get("simulated", False))
    device_name = settings.get("device_name", "Door Membrane Switch")
    topic = settings.get("topic")

    keys = settings.get("keys", ["1","2","3","A","4","5","6","B","7","8","9","C","*","0","#","D"])
    cb = lambda v, c: dms_callback(v, c, device_name, simulated, topic, pi_id, batch_sender, state)

    if simulated:
        t = threading.Thread(target=run_membrane_simulator, args=(poll_s, keys, cb, stop_event, code), daemon=True)
    else:
        from sensors.membrane_switch import run_membrane_switch_loop

        row_pins = settings.get("row_pins", [])
        col_pins = settings.get("col_pins", [])
        keymap = settings.get("keymap", [["1","2","3","A"],["4","5","6","B"],["7","8","9","C"],["*","0","#","D"]])
        debounce_ms = int(settings.get("debounce_ms", 200))

        t = threading.Thread(
            target=run_membrane_switch_loop,
            args=(row_pins, col_pins, keymap, poll_s, cb, stop_event, code),
            kwargs={"debounce_ms": debounce_ms},
            daemon=True,
        )

    t.start()
    threads.append(t)
