import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt

# Optional InfluxDB v2
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "iot")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "smart_home")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "home/#")

app = Flask(__name__)

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
    if isinstance(val, (int, float, bool, str)):
        p = p.field("value", val)
    else:
        p = p.field("value_str", json.dumps(val))

    # timestamp
    ts = payload.get("ts")
    if ts:
        # ts is epoch seconds
        p = p.time(datetime.utcfromtimestamp(float(ts)), WritePrecision.S)

    _influx_write.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)


def _publish_cmd(topic: str, data: dict):
    pub = mqtt.Client()
    pub.connect(MQTT_BROKER, MQTT_PORT, 60)
    pub.publish(topic, json.dumps(data))
    pub.disconnect()

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
                    write_to_influx(msg.topic, item)
        elif isinstance(payload, dict):
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

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "mqtt": {"broker": MQTT_BROKER, "port": MQTT_PORT, "topic": MQTT_TOPIC},
        "influx": {"enabled": _influx_write is not None, "url": INFLUX_URL, "bucket": INFLUX_BUCKET, "org": INFLUX_ORG}
    })

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
    return jsonify({"published_to": topic, "payload": data})


# Convenience GET endpoints so Grafana can trigger actuators via clickable links.
# (Grafana can't easily issue POST without plugins; GET keeps the demo simple.)

@app.get("/actuator/<pi_id>/led/on")
def led_on(pi_id: str):
    topic = f"home/{pi_id.lower()}/cmd/led"
    _publish_cmd(topic, {"state": True})
    return jsonify({"ok": True, "published_to": topic, "state": True})


@app.get("/actuator/<pi_id>/led/off")
def led_off(pi_id: str):
    topic = f"home/{pi_id.lower()}/cmd/led"
    _publish_cmd(topic, {"state": False})
    return jsonify({"ok": True, "published_to": topic, "state": False})


@app.get("/actuator/<pi_id>/led/toggle")
def led_toggle(pi_id: str):
    topic = f"home/{pi_id.lower()}/cmd/led"
    _publish_cmd(topic, {"action": "toggle"})
    return jsonify({"ok": True, "published_to": topic, "action": "toggle"})


@app.get("/actuator/<pi_id>/buzzer/beep")
def buzzer_beep(pi_id: str):
    ms = int(request.args.get("ms", "150"))
    count = int(request.args.get("count", "1"))
    gap_ms = int(request.args.get("gap_ms", "120"))
    topic = f"home/{pi_id.lower()}/cmd/buzzer"
    _publish_cmd(topic, {"action": "beep", "ms": ms, "count": count, "gap_ms": gap_ms})
    return jsonify({"ok": True, "published_to": topic, "action": "beep", "ms": ms, "count": count, "gap_ms": gap_ms})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
