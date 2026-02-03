import time
from typing import Any, Dict, Optional

def build_payload(pi_id: str, code: str, device_name: str, value: Any, simulated: bool, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "pi": pi_id,
        "code": code,
        "device_name": device_name,
        "value": value,
        "simulated": bool(simulated),
        "ts": time.time()
    }
    if extra:
        payload.update(extra)
    return payload
