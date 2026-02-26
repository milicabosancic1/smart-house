import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import paho.mqtt.client as mqtt
from system_state import SystemState

# Optional InfluxDB v2
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "iot")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "smart_home")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "home/#")
WEBC_URL = os.getenv("WEBC_URL", "")

# Ensure templates folder is found
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
system_state = SystemState()

_influx_write = None
try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    if INFLUX_TOKEN:
        _influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        _influx_write = _influx.write_api()
    else:
        _influx = None
except Exception:
    _influx = None
    _influx_write = None

def write_to_influx(topic: str, payload: dict):
    """Write one message to InfluxDB (if configured)."""
    if _influx_write is None:
        return

    # Use measurement based on code if present, else topic tail
    code = payload.get("code") or topic.split("/")[-1]
    measurement = f"sensor_{code}".lower()

    p = Point(measurement)
    # tags
    p = p.tag("pi", str(payload.get("pi", "")))
    p = p.tag("code", str(code))
    p = p.tag("device_name", str(payload.get("device_name", "")))
    p = p.tag("simulated", str(payload.get("simulated", False)).lower())
    p = p.tag("topic", topic)

    # fields
    val = payload.get("value")
    # Influx requires numeric/bool/string fields; we store as string if complex
    if isinstance(val, (int, float, bool)):
        p = p.field("value", val)
    elif isinstance(val, str):
        if str(code).upper() == "DMS":
            key_map = {
                "0": 0, "1": 1, "2": 2, "3": 3, "4": 4,
                "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
                "*": 10, "#": 11, "A": 12, "B": 13, "C": 14, "D": 15,
            }
            mapped = key_map.get(val.upper())
            if mapped is not None:
                p = p.field("value_num", mapped)
            p = p.field("value_str", val)
        else:
            p = p.field("value", val)
    elif isinstance(val, dict):
        # DHT-friendly flattening for Grafana panels
        if "temperature_c" in val:
            try:
                p = p.field("temperature_c", float(val.get("temperature_c")))
            except Exception:
                pass
        if "humidity_pct" in val:
            try:
                p = p.field("humidity_pct", float(val.get("humidity_pct")))
            except Exception:
                pass
        if "display" in val:
            p = p.field("display", str(val.get("display")))
        if "text" in val:
            p = p.field("text", str(val.get("text")))
        if "color" in val:
            p = p.field("color", str(val.get("color")))
        if "action" in val:
            p = p.field("action", str(val.get("action")))
        if "blink" in val:
            p = p.field("blink", bool(val.get("blink")))
        if "state" in val:
            p = p.field("state", bool(val.get("state")))
        if "ms" in val:
            try:
                p = p.field("ms", int(val.get("ms")))
            except Exception:
                pass
        if "count" in val:
            try:
                p = p.field("count", int(val.get("count")))
            except Exception:
                pass
        if "gap_ms" in val:
            try:
                p = p.field("gap_ms", int(val.get("gap_ms")))
            except Exception:
                pass
        p = p.field("value_str", json.dumps(val))
    else:
        p = p.field("value_str", json.dumps(val))

    # timestamp
    ts = payload.get("ts")
    if ts:
        # ts is epoch seconds
        p = p.time(datetime.utcfromtimestamp(float(ts)), WritePrecision.S)

    _influx_write.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)


def write_alarm_event_to_influx(event: dict):
    if _influx_write is None:
        return

    ts = float(event.get("ts", time.time()))
    state = str(event.get("event", ""))
    reason = str(event.get("reason", ""))

    p = Point("alarm_event")
    p = p.tag("source", "system")
    p = p.tag("event", state)
    p = p.tag("reason", reason)
    p = p.field("active", 1 if state == "on" else 0)
    p = p.field("reason_text", reason)
    p = p.time(datetime.utcfromtimestamp(ts), WritePrecision.S)

    _influx_write.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)


def _publish_cmd(topic: str, data: dict):
    pub = mqtt.Client()
    pub.connect(MQTT_BROKER, MQTT_PORT, 60)
    pub.publish(topic, json.dumps(data))
    pub.disconnect()


def _record_actuator_state(pi: str, code: str, device_name: str, value, topic: str):
    try:
        write_to_influx(
            topic,
            {
                "pi": pi,
                "code": code,
                "device_name": device_name,
                "value": value,
                "simulated": False,
                "ts": time.time(),
            },
        )
    except Exception as e:
        print(f"[INFLUX] actuator write error: {e}")


def _publish_alarm_buzzer(active: bool):
    topic = "home/pi1/cmd/buzzer"
    state = bool(active)
    _publish_cmd(topic, {"state": state})
    _record_actuator_state("PI1", "DB", "Door Buzzer", state, topic)


def _trigger_dl_10s():
    topic = "home/pi1/cmd/led"
    _publish_cmd(topic, {"state": True})
    _record_actuator_state("PI1", "DL", "Door Light", True, topic)

    def _off_later():
        time.sleep(10.0)
        _publish_cmd(topic, {"state": False})
        _record_actuator_state("PI1", "DL", "Door Light", False, topic)

    threading.Thread(target=_off_later, daemon=True).start()


def _sync_4sd(timer_seconds: int, blink: bool):
    mm = timer_seconds // 60
    ss = timer_seconds % 60
    topic = "home/pi2/cmd/4sd"
    value = {"display": f"{mm:02d}:{ss:02d}", "blink": bool(blink)}
    _publish_cmd(
        topic,
        value,
    )
    _record_actuator_state("PI2", "4SD", "Kitchen 4 Digit 7 Segment Display Timer", value, topic)


def _sync_lcd(text: str):
    topic = "home/pi3/cmd/lcd"
    value = {"text": text}
    _publish_cmd(topic, value)
    _record_actuator_state("PI3", "LCD", "Living room Display", value, topic)


def _sync_brgb(state: bool, color: str):
    topic = "home/pi3/cmd/brgb"
    value = {"state": bool(state), "color": color}
    _publish_cmd(topic, value)
    _record_actuator_state("PI3", "BRGB", "Bedroom RGB", value, topic)

def _handle_system_state(reading: dict):
    sensor = reading.get("code")
    value = reading.get("value")

    if sensor in {"DS1", "DS2"}:
        system_state.handle_door_sensor(sensor, value)
    elif sensor == "DMS":
        system_state.check_pin(value)
    elif sensor in {"DUS1", "DUS2"}:
        system_state.update_distance(sensor, value)
    elif sensor in {"DPIR1", "DPIR2", "DPIR3"}:
        out = system_state.handle_motion(sensor, value)
        if out.get("trigger_dl"):
            _trigger_dl_10s()
    elif sensor == "GSG":
        system_state.handle_gsg(value)
    elif sensor in {"DHT1", "DHT2", "DHT3"}:
        system_state.update_dht(sensor, value)
    elif sensor == "BTN":
        system_state.handle_btn(value)
    elif sensor == "IR":
        system_state.apply_ir(value)


def _system_rules_thread():
    last_alarm = None
    last_timer = None
    last_brgb = None
    last_lcd_rotate_ts = 0.0

    while True:
        try:
            system_state.check_time_rules()
            for event in system_state.pop_alarm_events():
                write_alarm_event_to_influx(event)

            snap = system_state.snapshot()

            alarm_active = bool(snap.get("alarm_active"))
            if alarm_active != last_alarm:
                _publish_alarm_buzzer(alarm_active)
                last_alarm = alarm_active

            timer_key = (
                int(snap.get("timer_seconds", 0)),
                bool(snap.get("timer_blink", False)),
                bool(snap.get("timer_running", False)),
            )
            if timer_key != last_timer:
                _sync_4sd(timer_key[0], timer_key[1])
                last_timer = timer_key

            brgb_key = (bool(snap.get("brgb_state", False)), str(snap.get("brgb_color", "#ffffff")))
            if brgb_key != last_brgb:
                _sync_brgb(brgb_key[0], brgb_key[1])
                last_brgb = brgb_key

            now = time.time()
            if now - last_lcd_rotate_ts >= 4.0:
                text = system_state.next_lcd_text()
                _sync_lcd(text)
                last_lcd_rotate_ts = now
        except Exception as e:
            print(f"[STATE] rules error: {e}")
        time.sleep(0.25)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        payload = {"raw": msg.payload.decode("utf-8", errors="ignore")}
    print(f"[MQTT] {msg.topic} -> {payload}")
    try:
        # KT2 batch mode: payload can be a LIST of readings
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    _handle_system_state(item)
                    write_to_influx(msg.topic, item)
        elif isinstance(payload, dict):
            _handle_system_state(payload)
            write_to_influx(msg.topic, payload)
    except Exception as e:
        print(f"[INFLUX] write error: {e}")

def mqtt_thread():
    c = mqtt.Client(client_id="smart-home-server")
    c.on_message = on_message
    c.connect(MQTT_BROKER, MQTT_PORT, 60)
    c.subscribe(MQTT_TOPIC)
    c.loop_forever()

# Start MQTT subscriber in background
t = threading.Thread(target=mqtt_thread, daemon=True)
t.start()

# Start system rules checker in background
t_rules = threading.Thread(target=_system_rules_thread, daemon=True)
t_rules.start()

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "mqtt": {"broker": MQTT_BROKER, "port": MQTT_PORT, "topic": MQTT_TOPIC},
        "influx": {"enabled": _influx_write is not None, "url": INFLUX_URL, "bucket": INFLUX_BUCKET, "org": INFLUX_ORG}
    })


@app.get("/state")
def get_state():
    return jsonify(system_state.snapshot())


@app.get("/")
def web_index():
    return render_template("index.html")


@app.post("/api/system/arm")
def api_system_arm():
    system_state.arm_system()
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/system/disarm")
def api_system_disarm():
    system_state.disarm_system()
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/alarm/on")
def api_alarm_on():
    system_state.activate_alarm("web")
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/alarm/off")
def api_alarm_off():
    system_state.deactivate_alarm()
    system_state.disarm_system()
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/timer/set")
def api_timer_set():
    data = request.get_json(force=True, silent=True) or {}
    seconds = int(data.get("seconds", 0))
    system_state.set_timer(seconds)
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/timer/add")
def api_timer_add():
    data = request.get_json(force=True, silent=True) or {}
    seconds = int(data.get("seconds", 0))
    system_state.add_timer_seconds(seconds)
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/timer/step")
def api_timer_step():
    data = request.get_json(force=True, silent=True) or {}
    seconds = int(data.get("seconds", 30))
    system_state.set_timer_add_step(seconds)
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/timer/start")
def api_timer_start():
    system_state.start_timer()
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/timer/stop")
def api_timer_stop():
    system_state.stop_timer()
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/timer/ack")
def api_timer_ack():
    system_state.ack_timer_blink()
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.post("/api/brgb")
def api_brgb():
    data = request.get_json(force=True, silent=True) or {}
    state = data.get("state")
    color = data.get("color")
    system_state.set_brgb(state=state, color=color)
    return jsonify({"ok": True, "state": system_state.snapshot()})


@app.get("/api/camera")
def api_camera():
    return jsonify({"ok": True, "url": WEBC_URL})

@app.post("/actuator/<pi_id>/<name>")
def actuator(pi_id: str, name: str):
    """Send actuator command over MQTT.

    Example:
      POST /actuator/pi1/led     {"state": true}
      POST /actuator/pi1/buzzer  {"action": "beep", "ms": 150, "count": 2}
    """
    data = request.get_json(force=True, silent=True) or {}
    topic = f"home/{pi_id.lower()}/cmd/{name.lower()}"
    _publish_cmd(topic, data)
    _record_actuator_state(pi_id.upper(), name.upper(), f"{name.upper()} actuator", data, topic)
    return jsonify({"published_to": topic, "payload": data})


# Convenience GET endpoints so Grafana can trigger actuators via clickable links.
# (Grafana can't easily issue POST without plugins; GET keeps the demo simple.)

@app.get("/actuator/<pi_id>/led/on")
def led_on(pi_id: str):
    topic = f"home/{pi_id.lower()}/cmd/led"
    value = {"state": True}
    _publish_cmd(topic, value)
    _record_actuator_state(pi_id.upper(), "DL", "Door Light", True, topic)
    return jsonify({"ok": True, "published_to": topic, "state": True})


@app.get("/actuator/<pi_id>/led/off")
def led_off(pi_id: str):
    topic = f"home/{pi_id.lower()}/cmd/led"
    value = {"state": False}
    _publish_cmd(topic, value)
    _record_actuator_state(pi_id.upper(), "DL", "Door Light", False, topic)
    return jsonify({"ok": True, "published_to": topic, "state": False})


@app.get("/actuator/<pi_id>/led/toggle")
def led_toggle(pi_id: str):
    topic = f"home/{pi_id.lower()}/cmd/led"
    value = {"action": "toggle"}
    _publish_cmd(topic, value)
    _record_actuator_state(pi_id.upper(), "DL", "Door Light", value, topic)
    return jsonify({"ok": True, "published_to": topic, "action": "toggle"})


@app.get("/actuator/<pi_id>/buzzer/beep")
def buzzer_beep(pi_id: str):
    ms = int(request.args.get("ms", "150"))
    count = int(request.args.get("count", "1"))
    gap_ms = int(request.args.get("gap_ms", "120"))
    topic = f"home/{pi_id.lower()}/cmd/buzzer"
    value = {"action": "beep", "ms": ms, "count": count, "gap_ms": gap_ms}
    _publish_cmd(topic, value)
    _record_actuator_state(pi_id.upper(), "DB", "Door Buzzer", value, topic)
    return jsonify({"ok": True, "published_to": topic, "action": "beep", "ms": ms, "count": count, "gap_ms": gap_ms})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
