import json
from typing import Any, Callable, Dict
import paho.mqtt.client as mqtt

MessageHandler = Callable[[str, Any], None]

class MQTTClient:
    def __init__(self, broker: str, port: int = 1883, client_id: str = "pi1-app"):
        self._client = mqtt.Client(client_id=client_id)
        self._client.connect(broker, int(port), 60)
        self._handlers = []  # list of (topic_prefix, handler)

        def _on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except Exception:
                payload = {"raw": msg.payload.decode("utf-8", errors="ignore")}

            topic = msg.topic
            for prefix, handler in self._handlers:
                if topic.startswith(prefix):
                    try:
                        handler(topic, payload)
                    except Exception as e:
                        print(f"[MQTT] handler error for {topic}: {e}")

        self._client.on_message = _on_message
        self._client.loop_start()

    def publish(self, topic: str, payload: Any) -> None:
        """Publish JSON-serializable payload.

        For KT2 we often publish batches (lists) as well as single dict payloads.
        """
        self._client.publish(topic, json.dumps(payload), qos=0, retain=False)

    def subscribe_prefix(self, topic_prefix: str, handler: MessageHandler) -> None:
        # subscribe wildcard under prefix
        wildcard = topic_prefix.rstrip("/") + "/#"
        self._client.subscribe(wildcard)
        self._handlers.append((topic_prefix.rstrip("/"), handler))

    def stop(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass
