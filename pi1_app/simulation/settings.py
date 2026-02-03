import json
from typing import Any, Dict, Tuple

def load_settings(filePath: str = 'settings.json') -> Dict[str, Any]:
    """Loads settings.

    Supports two formats:
    1) KT1 legacy: { "DS1": {...}, "DPIR1": {...}, ... }
    2) KT2 extended: { "global": {...}, "devices": { "DS1": {...}, ... } }
    """
    with open(filePath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Normalize to KT2-like structure
    if "devices" in data:
        if "global" not in data:
            data["global"] = {}
        return data

    # Legacy KT1 -> wrap
    return {
        "global": {
            "pi_id": "PI1",
            "mqtt": {
                "enabled": False
            }
        },
        "devices": data
    }
