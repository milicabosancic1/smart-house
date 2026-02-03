from dataclasses import dataclass, field
from typing import Any, Dict
import threading

@dataclass
class SharedState:
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    last: Dict[str, Any] = field(default_factory=dict, init=False)

    def set(self, code: str, value: Any):
        with self._lock:
            self.last[code] = value

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.last)
