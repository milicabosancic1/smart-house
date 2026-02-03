import threading
import time
from typing import List, Dict, Any

from simulation.components.dht import run_dht  # existing component

from simulation.simulators.button import run_button_simulator
from simulation.simulators.pir import run_pir_simulator
from simulation.simulators.ultrasonic import run_ultrasonic_simulator
from simulation.simulators.dms import run_dms_simulator

def ts_print(header: str, lines: List[str]):
    t = time.localtime()
    print("="*22)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print(header)
    for l in lines:
        print(l)

def cb_bool(value: bool, code: str):
    ts_print(f"Sensor event ({code})", [f"Value: {value}"])

def cb_distance(value: float, code: str):
    ts_print(f"Sensor reading ({code})", [f"Distance: {value:.1f} cm"])

def cb_dms(key: str, code: str):
    ts_print(f"Sensor event ({code})", [f"Key: {key}"])

def start_pi1_sensors(settings: Dict[str, Any], threads: List[threading.Thread], stop_event):
    """Start PI1 sensors based on settings.json."""

    # DS1 (Button)
    if "DS1" in settings:
        s = settings["DS1"]
        if s.get("simulated", True):
            th = threading.Thread(
                target=run_button_simulator,
                args=(s.get("delay", 0.5), cb_bool, stop_event, "DS1"),
                daemon=True
            )
        else:
            from simulation.sensors.button import run_button_loop
            th = threading.Thread(
                target=run_button_loop,
                args=(s["pin"], s.get("delay", 0.05), cb_bool, stop_event, s.get("pull_up", True)),
                daemon=True
            )
        th.start(); threads.append(th)

    # DPIR1 (Motion)
    if "DPIR1" in settings:
        s = settings["DPIR1"]
        if s.get("simulated", True):
            th = threading.Thread(
                target=run_pir_simulator,
                args=(s.get("delay", 1.0), cb_bool, stop_event, "DPIR1"),
                daemon=True
            )
        else:
            from simulation.sensors.pir import run_pir_loop
            th = threading.Thread(
                target=run_pir_loop,
                args=(s["pin"], s.get("delay", 0.1), cb_bool, stop_event),
                daemon=True
            )
        th.start(); threads.append(th)

    # DMS1 (Membrane switch / Keypad)
    if "DMS1" in settings:
        s = settings["DMS1"]
        # Za KT je dovoljan simulacioni režim.
        keys = s.get("keys", None)
        th = threading.Thread(
            target=run_dms_simulator,
            args=(s.get("delay", 2.0), cb_dms, stop_event, "DMS1", keys),
            daemon=True
        )
        th.start(); threads.append(th)

    # DUS1 (Ultrasonic)
    if "DUS1" in settings:
        s = settings["DUS1"]
        if s.get("simulated", True):
            th = threading.Thread(
                target=run_ultrasonic_simulator,
                args=(s.get("delay", 1.0), cb_distance, stop_event, "DUS1"),
                daemon=True
            )
        else:
            from simulation.sensors.ultrasonic import run_ultrasonic_loop
            th = threading.Thread(
                target=run_ultrasonic_loop,
                args=(s["trig_pin"], s["echo_pin"], s.get("delay", 1.0), cb_distance, stop_event),
                daemon=True
            )
        th.start(); threads.append(th)

    # Optional: DHT1 if present in settings
    if "DHT1" in settings:
        run_dht(settings["DHT1"], threads, stop_event)
