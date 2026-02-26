import threading
import time
from collections import deque

class SystemState:
    def __init__(self):
        self.lock = threading.Lock()

        # Alarm
        self.alarm_active = False
        self.system_armed = False
        self.pending_arm = False
        self._arm_delay_sec = 10.0
        self._alarm_reasons = set()
        self._alarm_events = []
        self._alarm_event_queue = []
        self.alarm_controls = {
            "door_open_too_long": True,
            "entry_delay_alarm": True,
            "motion_empty_house": True,
            "gsg_tilt": True,
        }

        # Broj osoba
        self.person_count = 0

        # PIN
        self.correct_pin = "1234"
        self._pin_buffer = ""

        # Kitchen timer
        self.timer_seconds = 0
        self.timer_running = False
        self._timer_blink = False
        self.timer_add_step = 30

        # Door sensors (DS1/DS2)
        self.ds_timeout_sec = 5.0
        self._door_open_since = {"DS1": None, "DS2": None}
        
        # Entry delay (PIN grace period when door opens while armed)
        self.entry_delay_sec = 30.0
        self._entry_delay_start = None
        self._entry_delay_active_for = None  # Track which sensor triggered entry delay

        # Motion/distance based counting
        self._distance_history = {
            "DUS1": deque(maxlen=8),
            "DUS2": deque(maxlen=8),
        }
        self._last_motion_ts = {
            "DPIR1": 0.0,
            "DPIR2": 0.0,
            "DPIR3": 0.0,
        }
        self._motion_debounce_sec = 2.0

        # Environment / display / RGB
        self.gsg_alarm_threshold = 20.0
        self.dht_values = {}
        self._lcd_order = ["DHT1", "DHT2", "DHT3"]
        self._lcd_index = 0
        self.lcd_text = ""
        self.brgb_state = False
        self.brgb_color = "#ffffff"

    # -------------------
    # ALARM
    # -------------------

    def _record_alarm_event(self, event: str, reason: str):
        entry = {"ts": time.time(), "event": event, "reason": reason}
        self._alarm_events.append(entry)
        self._alarm_event_queue.append(entry)
        if len(self._alarm_events) > 500:
            self._alarm_events = self._alarm_events[-250:]
        if len(self._alarm_event_queue) > 1000:
            self._alarm_event_queue = self._alarm_event_queue[-500:]

    def activate_alarm(self, reason: str = "manual"):
        with self.lock:
            self._alarm_reasons.add(reason)
            if not self.alarm_active:
                print("ALARM ACTIVATED")
                self.alarm_active = True
                self._record_alarm_event("on", reason)

    def deactivate_alarm(self, reason: str | None = None):
        with self.lock:
            if reason is None:
                self._alarm_reasons.clear()
            else:
                self._alarm_reasons.discard(reason)

            if self.alarm_active and not self._alarm_reasons:
                print("ALARM DEACTIVATED")
                self.alarm_active = False
                self._record_alarm_event("off", reason or "clear_all")

    def disarm_system(self):
        with self.lock:
            self.system_armed = False
            self.pending_arm = False

    def set_alarm_control(self, name: str, enabled: bool):
        with self.lock:
            if name not in self.alarm_controls:
                return False

            self.alarm_controls[name] = bool(enabled)
            if enabled:
                return True

            if name == "door_open_too_long":
                self._alarm_reasons = {r for r in self._alarm_reasons if not r.endswith("_open_too_long")}
            elif name == "entry_delay_alarm":
                self._alarm_reasons = {r for r in self._alarm_reasons if not r.endswith("_armed")}
            elif name == "motion_empty_house":
                self._alarm_reasons.discard("motion_empty_house")
            elif name == "gsg_tilt":
                self._alarm_reasons.discard("gsg_tilt")

            if self.alarm_active and not self._alarm_reasons:
                self.alarm_active = False
                self._record_alarm_event("off", f"rule_disabled:{name}")
            return True

    def trigger_scenario(self, name: str, params: dict | None = None):
        params = params or {}

        if name == "ds_open_too_long":
            sensor = str(params.get("sensor", "DS1")).upper()
            if sensor not in self._door_open_since:
                return {"ok": False, "error": "invalid sensor"}
            with self.lock:
                self._door_open_since[sensor] = time.time() - self.ds_timeout_sec - 0.2
            self.check_time_rules()
            return {"ok": True, "scenario": name, "sensor": sensor}

        if name == "entry_delay_expired":
            sensor = str(params.get("sensor", "DS1")).upper()
            if sensor not in self._door_open_since:
                return {"ok": False, "error": "invalid sensor"}
            with self.lock:
                self.system_armed = True
                self.pending_arm = False
                self._entry_delay_start = time.time() - self.entry_delay_sec - 0.2
                self._entry_delay_active_for = sensor
            self.check_time_rules()
            return {"ok": True, "scenario": name, "sensor": sensor}

        if name == "motion_empty_house":
            sensor = str(params.get("sensor", "DPIR3")).upper()
            if sensor not in self._last_motion_ts:
                return {"ok": False, "error": "invalid sensor"}
            with self.lock:
                self.person_count = 0
                self._last_motion_ts[sensor] = 0.0
            self.handle_motion(sensor, True)
            return {"ok": True, "scenario": name, "sensor": sensor}

        if name == "gsg_tilt":
            self.handle_gsg(self.gsg_alarm_threshold + 5.0)
            return {"ok": True, "scenario": name}

        return {"ok": False, "error": "unknown scenario"}

    # -------------------
    # ARMING SYSTEM
    # -------------------

    def arm_system(self):
        with self.lock:
            if self.system_armed or self.pending_arm:
                return
            self.pending_arm = True

        def delayed_arm():
            time.sleep(self._arm_delay_sec)
            with self.lock:
                if not self.pending_arm:
                    return
                self.system_armed = True
                self.pending_arm = False
                print("SYSTEM ARMED")

        threading.Thread(target=delayed_arm, daemon=True).start()

    def _check_pin_code(self, entered_pin: str):
        if entered_pin == self.correct_pin:
            # Cancel entry delay if active
            if self._entry_delay_start is not None:
                print(f"PIN OK — entry delay cancelled ({self._entry_delay_active_for})")
                self._entry_delay_start = None
                self._entry_delay_active_for = None
            
            if self.alarm_active:
                print("PIN OK — deactivating alarm")
                self.deactivate_alarm()
                self.disarm_system()
            else:
                print("PIN OK — arming system in 10 seconds")
                self.arm_system()
        else:
            print("WRONG PIN")

    def check_pin(self, entered_pin):
        if entered_pin is None:
            return

        raw = str(entered_pin).strip()
        if not raw:
            return

        if raw.isdigit() and len(raw) == 4:
            self._check_pin_code(raw)
            return

        with self.lock:
            if raw == "*":
                self._pin_buffer = ""
                return

            if raw == "#":
                candidate = self._pin_buffer
                self._pin_buffer = ""
            elif len(raw) == 1 and raw.isdigit():
                self._pin_buffer = (self._pin_buffer + raw)[-4:]
                return
            else:
                return

        if candidate:
            self._check_pin_code(candidate)

    # -------------------
    # PERSON COUNT
    # -------------------

    def person_entered(self):
        with self.lock:
            self.person_count += 1
            print("PERSON ENTERED:", self.person_count)

    def person_left(self):
        with self.lock:
            if self.person_count > 0:
                self.person_count -= 1
            print("PERSON LEFT:", self.person_count)

    def handle_door_sensor(self, sensor: str, value):
        if sensor not in self._door_open_since:
            return

        active = bool(value)
        now = time.time()

        with self.lock:
            open_since = self._door_open_since[sensor]
            if active:
                if open_since is None:
                    self._door_open_since[sensor] = now
                if self.system_armed and self._entry_delay_start is None:
                    # Start entry delay grace period instead of immediate alarm
                    self._entry_delay_start = now
                    self._entry_delay_active_for = sensor
                    print(f"ENTRY DELAY STARTED ({sensor}): {self.entry_delay_sec}s to enter PIN or alarm sounds")
            else:
                self._door_open_since[sensor] = None
                # If door closes during entry delay, cancel it
                if self._entry_delay_start is not None and self._entry_delay_active_for == sensor:
                    print(f"Entry delay cancelled ({sensor} closed)")
                    self._entry_delay_start = None
                    self._entry_delay_active_for = None
                self._alarm_reasons.discard(f"{sensor}_open_too_long")
                if self.alarm_active and not self._alarm_reasons:
                    print("ALARM DEACTIVATED")
                    self.alarm_active = False
                    self._record_alarm_event("off", f"{sensor}_closed")

    def check_time_rules(self):
        now = time.time()
        with self.lock:
            # Check entry delay (PIN grace period when door opens while armed)
            if self._entry_delay_start is not None:
                if now - self._entry_delay_start >= self.entry_delay_sec:
                    sensor = self._entry_delay_active_for
                    if self.alarm_controls.get("entry_delay_alarm", True):
                        print(f"ENTRY DELAY EXPIRED ({sensor}): Activating alarm")
                        self._alarm_reasons.add(f"{sensor}_armed")
                        if not self.alarm_active:
                            print("ALARM ACTIVATED")
                            self.alarm_active = True
                            self._record_alarm_event("on", f"{sensor}_armed")
                    self._entry_delay_start = None
                    self._entry_delay_active_for = None
            
            # Check DS timeout (door open too long)
            for sensor, open_since in self._door_open_since.items():
                if open_since is None:
                    continue

                if now - open_since >= self.ds_timeout_sec and self.alarm_controls.get("door_open_too_long", True):
                    self._alarm_reasons.add(f"{sensor}_open_too_long")
                    if not self.alarm_active:
                        print("ALARM ACTIVATED")
                        self.alarm_active = True
                        self._record_alarm_event("on", f"{sensor}_open_too_long")

    def snapshot(self):
        with self.lock:
            now = time.time()
            entry_delay_remaining = 0
            if self._entry_delay_start is not None:
                remaining = self.entry_delay_sec - (now - self._entry_delay_start)
                entry_delay_remaining = max(0, remaining)
            
            return {
                "alarm_active": self.alarm_active,
                "system_armed": self.system_armed,
                "pending_arm": self.pending_arm,
                "entry_delay_active": self._entry_delay_start is not None,
                "entry_delay_remaining": entry_delay_remaining,
                "entry_delay_sensor": self._entry_delay_active_for,
                "alarm_controls": dict(self.alarm_controls),
                "person_count": self.person_count,
                "alarm_reasons": sorted(self._alarm_reasons),
                "alarm_events": list(self._alarm_events[-100:]),
                "door_open_since": dict(self._door_open_since),
                "timer_seconds": self.timer_seconds,
                "timer_running": self.timer_running,
                "timer_blink": self._timer_blink,
                "timer_add_step": self.timer_add_step,
                "dht_values": dict(self.dht_values),
                "lcd_text": self.lcd_text,
                "brgb_state": self.brgb_state,
                "brgb_color": self.brgb_color,
            }

    def pop_alarm_events(self):
        with self.lock:
            if not self._alarm_event_queue:
                return []
            events = list(self._alarm_event_queue)
            self._alarm_event_queue.clear()
            return events

    def update_distance(self, sensor: str, value):
        if sensor not in self._distance_history:
            return
        try:
            dist = float(value)
        except Exception:
            return
        with self.lock:
            self._distance_history[sensor].append((time.time(), dist))

    def _infer_direction(self, dus_sensor: str):
        hist = list(self._distance_history.get(dus_sensor, []))
        if len(hist) < 4:
            return None

        vals = [v for _, v in hist]
        mid = len(vals) // 2
        old_avg = sum(vals[:mid]) / max(1, len(vals[:mid]))
        new_avg = sum(vals[mid:]) / max(1, len(vals[mid:]))

        if new_avg < old_avg - 10.0:
            return "enter"
        if new_avg > old_avg + 10.0:
            return "exit"
        return None

    def handle_motion(self, sensor: str, value):
        if sensor not in self._last_motion_ts:
            return {"direction": None, "trigger_dl": False}

        active = bool(value)
        if not active:
            return {"direction": None, "trigger_dl": False}

        now = time.time()
        with self.lock:
            if now - self._last_motion_ts[sensor] < self._motion_debounce_sec:
                return {"direction": None, "trigger_dl": False}
            self._last_motion_ts[sensor] = now

        dus_sensor = "DUS1" if sensor == "DPIR1" else "DUS2" if sensor == "DPIR2" else None
        direction = self._infer_direction(dus_sensor) if dus_sensor else None

        if direction == "enter":
            self.person_entered()
        elif direction == "exit":
            self.person_left()

        with self.lock:
            if self.person_count == 0 and self.alarm_controls.get("motion_empty_house", True):
                self._alarm_reasons.add("motion_empty_house")
                if not self.alarm_active:
                    print("ALARM ACTIVATED")
                    self.alarm_active = True
                    self._record_alarm_event("on", "motion_empty_house")

        return {"direction": direction, "trigger_dl": sensor == "DPIR1"}

    def handle_gsg(self, value):
        try:
            movement = float(value)
        except Exception:
            return

        if movement >= self.gsg_alarm_threshold and self.alarm_controls.get("gsg_tilt", True):
            self.activate_alarm("gsg_tilt")

    def update_dht(self, sensor: str, value):
        if sensor not in {"DHT1", "DHT2", "DHT3"}:
            return
        if not isinstance(value, dict):
            return
        with self.lock:
            self.dht_values[sensor] = {
                "temperature_c": value.get("temperature_c"),
                "humidity_pct": value.get("humidity_pct"),
                "ts": time.time(),
            }

    def next_lcd_text(self):
        with self.lock:
            available = [key for key in self._lcd_order if key in self.dht_values]
            if not available:
                self.lcd_text = "No DHT data"
                return self.lcd_text

            pick = available[self._lcd_index % len(available)]
            self._lcd_index += 1
            d = self.dht_values.get(pick, {})
            t = d.get("temperature_c")
            h = d.get("humidity_pct")
            self.lcd_text = f"{pick} T:{t}C H:{h}%"
            return self.lcd_text

    def set_timer_add_step(self, seconds: int):
        with self.lock:
            self.timer_add_step = max(1, int(seconds))

    def handle_btn(self, pressed):
        if not bool(pressed):
            return
        with self.lock:
            add = self.timer_add_step
            self._timer_blink = False
        self.add_timer_seconds(add)

    def set_brgb(self, state: bool | None = None, color: str | None = None):
        with self.lock:
            if state is not None:
                self.brgb_state = bool(state)
            if color:
                self.brgb_color = str(color)

    def apply_ir(self, value):
        if isinstance(value, dict):
            cmd = str(value.get("command", "")).lower()
            color = value.get("color")
        else:
            cmd = str(value).lower()
            color = None

        if cmd in {"on", "power_on"}:
            self.set_brgb(state=True)
        elif cmd in {"off", "power_off"}:
            self.set_brgb(state=False)
        elif cmd in {"toggle", "power"}:
            with self.lock:
                self.brgb_state = not self.brgb_state
        elif cmd.startswith("color:"):
            self.set_brgb(state=True, color=cmd.split(":", 1)[1])
        elif color:
            self.set_brgb(state=True, color=color)

    def set_timer(self, seconds: int):
        with self.lock:
            self.timer_seconds = max(0, int(seconds))
            self._timer_blink = False

    def add_timer_seconds(self, seconds: int):
        with self.lock:
            self.timer_seconds = max(0, self.timer_seconds + int(seconds))

    def stop_timer(self):
        with self.lock:
            self.timer_running = False

    def start_timer(self):
        with self.lock:
            if self.timer_running or self.timer_seconds <= 0:
                return
            self.timer_running = True
            self._timer_blink = False

        def loop():
            while True:
                time.sleep(1.0)
                with self.lock:
                    if not self.timer_running:
                        return

                    if self.timer_seconds > 0:
                        self.timer_seconds -= 1

                    if self.timer_seconds <= 0:
                        self.timer_seconds = 0
                        self.timer_running = False
                        self._timer_blink = True
                        return

        threading.Thread(target=loop, daemon=True).start()

    def ack_timer_blink(self):
        with self.lock:
            self._timer_blink = False