import threading
from typing import Optional

from utils.printing import banner
from utils.state import SharedState
from utils.device_payload import build_payload

from simulators.ultrasonic import run_ultrasonic_simulator

def dus_callback(distance_cm: float, code: str, device_name: str, simulated: bool, topic: Optional[str],
                 pi_id: str, batch_sender, state: SharedState):
    banner(code)
    print(f"Distance: {distance_cm:.1f} cm")
    state.set(code, {"distance_cm": float(distance_cm)})

    if batch_sender is not None and topic:
        payload = build_payload(pi_id, code, device_name, float(distance_cm), simulated, extra={"unit": "cm", "kind": "ultrasonic"})
        batch_sender.enqueue(topic, payload)

def run_dus1(settings: dict, threads: list, stop_event: threading.Event, state: SharedState,
             pi_id: str = "PI1", batch_sender=None):
    if not settings.get("enabled", True):
        return
    code = settings.get("code", "DUS1")
    poll_s = float(settings.get("poll_s", 1.0))
    simulated = bool(settings.get("simulated", False))
    device_name = settings.get("device_name", "Door Ultrasonic Sensor")
    topic = settings.get("topic")

    cb = lambda v, c: dus_callback(v, c, device_name, simulated, topic, pi_id, batch_sender, state)

    if simulated:
        t = threading.Thread(target=run_ultrasonic_simulator, args=(poll_s, cb, stop_event, code), daemon=True)
    else:
        from sensors.ultrasonic import UltrasonicSensor, run_ultrasonic_loop
        sensor = UltrasonicSensor(settings["trigger_pin"], settings["echo_pin"])
        t = threading.Thread(target=run_ultrasonic_loop, args=(sensor, poll_s, cb, stop_event, code), daemon=True)
    t.start()
    threads.append(t)
