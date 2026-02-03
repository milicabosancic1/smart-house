import threading
from typing import Optional

from utils.printing import banner
from utils.state import SharedState
from utils.device_payload import build_payload

from simulators.button import run_button_simulator


def ds1_callback(pressed: bool, code: str, device_name: str, simulated: bool, topic: Optional[str],
                 pi_id: str, batch_sender, state: SharedState):
    banner(code)
    print(f"Pressed: {pressed}")
    state.set(code, {"pressed": pressed})

    if batch_sender is not None and topic:
        payload = build_payload(pi_id, code, device_name, pressed, simulated, extra={"kind": "button"})
        batch_sender.enqueue(topic, payload)


def run_ds1(settings: dict, threads: list, stop_event: threading.Event, state: SharedState,
            pi_id: str = "PI1", batch_sender=None):
    if not settings.get("enabled", True):
        return

    code = "DS1"
    poll_s = float(settings.get("poll_s", 0.1))
    simulated = bool(settings.get("simulated", False))
    device_name = settings.get("device_name", "Door Sensor")
    topic = settings.get("topic")

    cb = lambda v, c: ds1_callback(v, c, device_name, simulated, topic, pi_id, batch_sender, state)

    if simulated:
        t = threading.Thread(target=run_button_simulator, args=(poll_s, cb, stop_event, code), daemon=True)
    else:
        from sensors.button import ButtonSensor, run_button

        sensor = ButtonSensor(
            pin=int(settings["pin"]),
            pull=settings.get("pull", "UP"),
            invert=settings.get("invert"),
        )
        t = threading.Thread(
            target=run_button,
            args=(sensor, poll_s, cb, stop_event, code),
            kwargs={
                "use_events": bool(settings.get("use_events", True)),
                "bouncetime_ms": int(settings.get("debounce_ms", 150)),
            },
            daemon=True,
        )

    t.start()
    threads.append(t)
