import random
import threading
import time
from typing import Optional

from utils.printing import banner
from utils.state import SharedState
from utils.device_payload import build_payload


def _emit_value(value, code: str, device_name: str, simulated: bool, topic: Optional[str],
                pi_id: str, batch_sender, state: SharedState, extra: Optional[dict] = None):
    banner(code)
    print(f"Value: {value}")
    state.set(code, {"value": value})

    if batch_sender is not None and topic:
        payload = build_payload(pi_id, code, device_name, value, simulated, extra=extra or {})
        batch_sender.enqueue(topic, payload)


def run_dht(settings: dict, threads: list, stop_event: threading.Event, state: SharedState,
            pi_id: str = "PI1", batch_sender=None):
    if not settings.get("enabled", True):
        return

    code = settings.get("code", "DHT")
    poll_s = float(settings.get("poll_s", 2.0))
    simulated = bool(settings.get("simulated", True))
    device_name = settings.get("device_name", "DHT Sensor")
    topic = settings.get("topic")

    temp_min = float(settings.get("temp_min", 19.0))
    temp_max = float(settings.get("temp_max", 28.0))
    hum_min = float(settings.get("hum_min", 30.0))
    hum_max = float(settings.get("hum_max", 65.0))

    def loop():
        while not stop_event.is_set():
            temperature = round(random.uniform(temp_min, temp_max), 1)
            humidity = round(random.uniform(hum_min, hum_max), 1)

            payload_value = {
                "temperature_c": temperature,
                "humidity_pct": humidity,
            }
            _emit_value(
                payload_value,
                code,
                device_name,
                simulated,
                topic,
                pi_id,
                batch_sender,
                state,
                extra={"kind": "dht"},
            )
            time.sleep(poll_s)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    threads.append(t)


def run_gsg(settings: dict, threads: list, stop_event: threading.Event, state: SharedState,
            pi_id: str = "PI1", batch_sender=None):
    if not settings.get("enabled", True):
        return

    code = settings.get("code", "GSG")
    poll_s = float(settings.get("poll_s", 0.6))
    simulated = bool(settings.get("simulated", True))
    device_name = settings.get("device_name", "Gyroscope")
    topic = settings.get("topic")

    base_jitter = float(settings.get("base_jitter_deg", 2.5))
    spike_chance = float(settings.get("spike_chance", 0.08))
    spike_min = float(settings.get("spike_min_deg", 20.0))
    spike_max = float(settings.get("spike_max_deg", 55.0))

    def loop():
        while not stop_event.is_set():
            if random.random() < spike_chance:
                movement = round(random.uniform(spike_min, spike_max), 2)
            else:
                movement = round(random.uniform(0.0, base_jitter), 2)

            _emit_value(
                movement,
                code,
                device_name,
                simulated,
                topic,
                pi_id,
                batch_sender,
                state,
                extra={"unit": "deg", "kind": "gyro"},
            )
            time.sleep(poll_s)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    threads.append(t)


def run_ir(settings: dict, threads: list, stop_event: threading.Event, state: SharedState,
           pi_id: str = "PI1", batch_sender=None):
    if not settings.get("enabled", True):
        return

    code = settings.get("code", "IR")
    poll_s = float(settings.get("poll_s", 3.0))
    simulated = bool(settings.get("simulated", True))
    device_name = settings.get("device_name", "Infrared Remote")
    topic = settings.get("topic")

    colors = settings.get("colors", ["#ff0000", "#00ff00", "#0000ff", "#ffffff"])
    cmds = settings.get("commands", ["toggle", "color", "off", "on"])

    def loop():
        while not stop_event.is_set():
            cmd = random.choice(cmds)
            if cmd == "color":
                value = {"command": "color", "color": random.choice(colors)}
            else:
                value = {"command": cmd}

            _emit_value(value, code, device_name, simulated, topic, pi_id, batch_sender, state, extra={"kind": "ir"})
            time.sleep(poll_s)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    threads.append(t)
