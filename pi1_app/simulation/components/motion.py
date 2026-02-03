import threading
from typing import Optional

from utils.printing import banner
from utils.state import SharedState
from utils.device_payload import build_payload

from simulators.pir import run_pir_simulator

def pir_callback(motion: bool, code: str, device_name: str, simulated: bool, topic: Optional[str],
                 pi_id: str, batch_sender, state: SharedState):
    banner(code)
    print(f"Motion: {motion}")
    state.set(code, {"motion": motion})

    if batch_sender is not None and topic:
        payload = build_payload(pi_id, code, device_name, motion, simulated, extra={"kind": "pir"})
        batch_sender.enqueue(topic, payload)

def run_dpir1(settings: dict, threads: list, stop_event: threading.Event, state: SharedState,
              pi_id: str = "PI1", batch_sender=None):
    if not settings.get("enabled", True):
        return
    code = "DPIR1"
    poll_s = float(settings.get("poll_s", 0.2))
    simulated = bool(settings.get("simulated", False))
    device_name = settings.get("device_name", "Door Motion Sensor")
    topic = settings.get("topic")

    cb = lambda v, c: pir_callback(v, c, device_name, simulated, topic, pi_id, batch_sender, state)

    if simulated:
        t = threading.Thread(target=run_pir_simulator, args=(poll_s, cb, stop_event, code), daemon=True)
    else:
        from sensors.pir import PirSensor, run_pir
        sensor = PirSensor(int(settings["pin"]), pull=settings.get("pull"))
        t = threading.Thread(target=run_pir, args=(sensor, poll_s, cb, stop_event, code), kwargs={"use_events": bool(settings.get("use_events", True))}, daemon=True)
    t.start()
    threads.append(t)
