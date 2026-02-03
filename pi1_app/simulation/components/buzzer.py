from typing import Optional
from utils.device_payload import build_payload

from components.actuators import SimBuzzer

class PublishingBuzzer:
    def __init__(self, inner, *, pi_id: str, code: str, device_name: str, simulated: bool, topic: Optional[str], batch_sender):
        self._inner = inner
        self._pi_id = pi_id
        self._code = code
        self._device_name = device_name
        self._simulated = simulated
        self._topic = topic
        self._batch = batch_sender

    @property
    def state(self):
        return getattr(self._inner, "state", None)

    def _publish(self):
        if self._batch is None or not self._topic:
            return
        payload = build_payload(self._pi_id, self._code, self._device_name, bool(self.state), self._simulated, extra={"kind": "actuator", "unit": "bool"})
        self._batch.enqueue(self._topic, payload)

    def setup(self):
        self._inner.setup()
        self._publish()

    def on(self):
        self._inner.on()
        self._publish()

    def off(self):
        self._inner.off()
        self._publish()

    def beep(self, ms: int = 150, count: int = 1, gap_ms: int = 120):
        self._inner.beep(ms, count, gap_ms)
        # optional: publish a pulse event (not a state)
        if self._batch is not None and self._topic:
            payload = build_payload(self._pi_id, self._code, self._device_name, "beep", self._simulated, extra={"kind": "actuator_event", "ms": ms, "count": count, "gap_ms": gap_ms})
            self._batch.enqueue(self._topic, payload)

def build_buzzer(settings: dict, *, pi_id: str = "PI1", batch_sender=None):
    if not settings.get("enabled", True):
        return None

    simulated = bool(settings.get("simulated", False))
    device_name = settings.get("device_name", "Door Buzzer")
    topic = settings.get("topic")
    code = "DB"

    if simulated:
        b = SimBuzzer()
        b.setup()
    else:
        from sensors.buzzer import BuzzerActuator
        b = BuzzerActuator(settings["pin"])
        b.setup()

    return PublishingBuzzer(b, pi_id=pi_id, code=code, device_name=device_name, simulated=simulated, topic=topic, batch_sender=batch_sender)
