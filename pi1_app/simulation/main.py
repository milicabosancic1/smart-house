import threading
import time

from settings import load_settings
from utils.state import SharedState

from components.door_sensor import run_ds1
from components.motion import run_dpir1
from components.ultrasonic import run_dus1
from components.membrane_switch import run_dms
from components.led import build_led
from components.buzzer import build_buzzer
from components.console import run_console


def start_sensors(devices: dict, threads: list, stop_event: threading.Event, state: SharedState,
                  pi_id: str, batch_sender=None):
    # Start only devices present in config
    if "DS1" in devices:
        run_ds1(devices["DS1"], threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
    if "DPIR1" in devices:
        run_dpir1(devices["DPIR1"], threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
    if "DUS1" in devices:
        run_dus1(devices["DUS1"], threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
    if "DMS" in devices:
        run_dms(devices["DMS"], threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)


if __name__ == "__main__":
    settings = load_settings()

    global_cfg = settings.get("global", {})
    devices = settings.get("devices", {})

    pi_id = global_cfg.get("pi_id", "PI1")

    print(f"Starting PI1 app (KT1+KT2) on {pi_id}")

    threads: list[threading.Thread] = []
    stop_event = threading.Event()
    state = SharedState()

    mqtt_client = None
    batch_sender = None

    # KT2: optional MQTT + batch sender
    mqtt_cfg = global_cfg.get("mqtt") or {}
    mqtt_enabled = bool(mqtt_cfg.get("enabled", False))

    if mqtt_enabled:
        try:
            from utils.mqtt_client import MQTTClient
            from utils.batch_sender import BatchSender

            broker = mqtt_cfg.get("broker", "localhost")
            port = int(mqtt_cfg.get("port", 1883))
            interval = float(mqtt_cfg.get("batch_interval_sec", 5))

            mqtt_client = MQTTClient(broker, port=port, client_id=f"{pi_id}-pi1-app")
            batch_sender = BatchSender(mqtt_client, batch_interval_sec=interval)
            batch_sender.start()
            print(f"[MQTT] enabled -> broker={broker}:{port} batch_interval={interval}s")
        except Exception as e:
            print(f"[MQTT] FAILED to start MQTT/batch sender: {e}")
            mqtt_client = None
            batch_sender = None

    # Actuators (DL/DB)
    led = build_led(devices.get("DL", {"enabled": False}), pi_id=pi_id, batch_sender=batch_sender)
    buzzer = build_buzzer(devices.get("DB", {"enabled": False}), pi_id=pi_id, batch_sender=batch_sender)

    # KT2: optional command listener (control actuators via MQTT)
    if mqtt_client is not None:
        cmd_prefix = f"home/{pi_id.lower()}/cmd"

        def handle_cmd(topic: str, payload: dict):
            leaf = topic.split("/")[-1].lower()

            if leaf == "led" and led is not None:
                action = str(payload.get("action", "")).lower()
                if "state" in payload:
                    led.on() if bool(payload["state"]) else led.off()
                elif action == "toggle":
                    led.toggle()

            elif leaf == "buzzer" and buzzer is not None:
                action = str(payload.get("action", "")).lower()
                if "state" in payload:
                    buzzer.on() if bool(payload["state"]) else buzzer.off()
                elif action == "beep":
                    ms = int(payload.get("ms", 150))
                    count = int(payload.get("count", 1))
                    gap_ms = int(payload.get("gap_ms", 120))
                    buzzer.beep(ms, count, gap_ms)

        mqtt_client.subscribe_prefix(cmd_prefix, handle_cmd)
        print(f"[MQTT] command listener ON -> {cmd_prefix}/#")

    # Start sensors threads
    start_sensors(devices, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)

    try:
        # Console runs in main thread (clean Ctrl+C handling)
        run_console(led, buzzer, state)
    finally:
        # stop loops
        stop_event.set()
        if batch_sender is not None:
            batch_sender.stop()
        if mqtt_client is not None:
            mqtt_client.stop()

        # join threads briefly
        for t in threads:
            try:
                t.join(timeout=1.0)
            except Exception:
                pass

        try:
            from utils.gpio_compat import cleanup as gpio_cleanup
            gpio_cleanup()
        except Exception:
            pass

        print("PI1 app stopped.")
