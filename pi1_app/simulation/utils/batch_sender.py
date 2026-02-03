import threading
import time
import queue
from typing import Any, Dict, Optional

class BatchSender(threading.Thread):
    """Daemon thread that periodically flushes queued MQTT messages.

    Uses queue.Queue which is thread-safe -> minimal locking and no deadlocks.
    Each item is a dict: { "topic": str, "payload": dict }

    Batch semantics (KT2):
      - we flush every N seconds
      - we GROUP queued messages per topic
      - we publish ONE MQTT message per topic whose payload is a LIST of readings
    """
    def __init__(self, mqtt_client, batch_interval_sec: float = 5.0, max_batch: int = 500):
        super().__init__(daemon=True)
        self._q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._mqtt = mqtt_client
        self._interval = float(batch_interval_sec)
        self._max_batch = int(max_batch)
        self._stop_event = threading.Event()

    def enqueue(self, topic: str, payload: Dict[str, Any]) -> None:
        self._q.put({"topic": topic, "payload": payload})

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            batch = []
            try:
                # collect up to max_batch without blocking
                while len(batch) < self._max_batch:
                    batch.append(self._q.get_nowait())
            except queue.Empty:
                pass

            if batch:
                # group by topic and publish list payload per topic
                grouped = {}
                for item in batch:
                    grouped.setdefault(item["topic"], []).append(item["payload"])

                for topic, payloads in grouped.items():
                    try:
                        self._mqtt.publish(topic, payloads)
                    except Exception as e:
                        # Do not crash the daemon; print and continue
                        print(f"[BATCH] publish error: {e}")

            time.sleep(self._interval)
