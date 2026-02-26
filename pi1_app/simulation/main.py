import threading
import time
import os
import subprocess

from settings import load_settings
from utils.state import SharedState

from components.door_sensor import run_ds1
from components.motion import run_dpir1
from components.ultrasonic import run_dus1
from components.membrane_switch import run_dms
from components.environment import run_dht, run_gsg, run_ir
from components.led import build_led
from components.buzzer import build_buzzer
from components.console import run_console


def start_sensors(devices: dict, threads: list, stop_event: threading.Event, state: SharedState,
                  pi_id: str, batch_sender=None):
    for code, cfg in devices.items():
        settings = dict(cfg)
        settings["code"] = code

        if code.startswith("DS"):
            run_ds1(settings, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
        elif code.startswith("DPIR"):
            run_dpir1(settings, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
        elif code.startswith("DUS"):
            run_dus1(settings, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
        elif code == "DMS":
            run_dms(settings, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
        elif code == "BTN":
            run_ds1(settings, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
        elif code.startswith("DHT"):
            run_dht(settings, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
        elif code == "GSG":
            run_gsg(settings, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)
        elif code == "IR":
            run_ir(settings, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)


if __name__ == "__main__":
    settings_file = os.getenv("SIM_SETTINGS_FILE", "settings.json")
    settings = load_settings(settings_file)

    global_cfg = settings.get("global", {})
    devices = settings.get("devices", {})

    pi_id = global_cfg.get("pi_id", "PI1")

    print(f"Starting Smart Home app (KT1+KT2) on {pi_id} using {settings_file}")

    threads: list[threading.Thread] = []
    stop_event = threading.Event()
    state = SharedState()
    webcam_proc = None

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

            mqtt_client = MQTTClient(broker, port=port, client_id=f"{pi_id.lower()}-app")
            batch_sender = BatchSender(mqtt_client, batch_interval_sec=interval)
            batch_sender.start()
            print(f"[MQTT] enabled -> broker={broker}:{port} batch_interval={interval}s")
        except Exception as e:
            print(f"[MQTT] FAILED to start MQTT/batch sender: {e}")
            mqtt_client = None
            batch_sender = None

    # Optional PI webcam stream (WEBC) via mjpg_streamer
    webcam_cfg = global_cfg.get("webcam") or {}
    webcam_enabled = bool(webcam_cfg.get("enabled", False))
    webcam_autostart = bool(webcam_cfg.get("auto_start", False))
    webcam_cmd = webcam_cfg.get(
        "streamer_cmd",
        'mjpg_streamer -i "input_uvc.so" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www"',
    )
    webcam_url = webcam_cfg.get("stream_url", "")

    if webcam_enabled:
        if webcam_url:
            print(f"[WEBC] stream url: {webcam_url}")

        if webcam_autostart:
            try:
                webcam_proc = subprocess.Popen(
                    webcam_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print("[WEBC] mjpg_streamer started from Python")
            except Exception as e:
                webcam_proc = None
                print(f"[WEBC] FAILED to start mjpg_streamer: {e}")

    # Actuators (DL/DB), present only for PI configs that define them
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

            elif leaf == "4sd":
                display = payload.get("display", "00:00")
                blink = bool(payload.get("blink", False))
                state.set("4SD", {"display": display, "blink": blink})
                print(f"[4SD] display={display} blink={blink}")

            elif leaf == "lcd":
                text = str(payload.get("text", ""))
                state.set("LCD", {"text": text})
                print(f"[LCD] {text}")

            elif leaf == "brgb":
                rgb_state = bool(payload.get("state", False))
                color = str(payload.get("color", "#ffffff"))
                state.set("BRGB", {"state": rgb_state, "color": color})
                print(f"[BRGB] state={rgb_state} color={color}")

        mqtt_client.subscribe_prefix(cmd_prefix, handle_cmd)
        print(f"[MQTT] command listener ON -> {cmd_prefix}/#")

    # Start sensors threads
    start_sensors(devices, threads, stop_event, state, pi_id=pi_id, batch_sender=batch_sender)

    try:
        # Console runs in main thread (clean Ctrl+C handling)
        run_console(led, buzzer, state, pi_id=pi_id)
    finally:
        # stop loops
        stop_event.set()
        if batch_sender is not None:
            batch_sender.stop()
        if mqtt_client is not None:
            mqtt_client.stop()

        if webcam_proc is not None:
            try:
                webcam_proc.terminate()
            except Exception:
                pass

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

        print("Smart Home app stopped.")
