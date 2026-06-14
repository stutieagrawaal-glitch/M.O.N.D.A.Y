import threading
import requests
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from core.attention import AttentionSystem
from core.memory import MemorySystem
from core.presence import PresenceTracker
from core.states import SensorEvent, SensorType, SystemState
from appliances.controller import ApplianceController
from intelligence.prediction import PredictionEngine
from intelligence.anomaly import AnomalyDetector
from intelligence.recommendation import RecommendationEngine
from alerts.notifications import NotificationSystem
from alerts.emergency import EmergencyHandler

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

def _ask_ollama(prompt: str, timeout: int = 10) -> Optional[str]:
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception:
        pass
    return None

def _ollama_async(prompt: str, callback):
    def _run():
        result = _ask_ollama(prompt)
        if result:
            callback(result)
    threading.Thread(target=_run, daemon=True).start()


class Monday:

    def __init__(self):
        self.state         = SystemState.LOW_POWER
        self.memory        = MemorySystem()
        self.attention     = AttentionSystem()
        self.presence      = PresenceTracker()
        self.appliances    = ApplianceController()
        self.predictor     = PredictionEngine(self.memory)
        self.anomaly       = AnomalyDetector(self.memory)
        self.recommender   = RecommendationEngine(self.memory)
        self.notifications = NotificationSystem()
        self.emergency     = EmergencyHandler(self.notifications)
        self.user_asleep   = False
        self.event_log: List[Dict] = []
        self.ollama_available: Optional[bool] = None

    def log(self, message: str, level: str = "info"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level":     level,
            "message":   message,
        }
        self.event_log.append(entry)
        if len(self.event_log) > 200:
            self.event_log.pop(0)
        print(message)
        return entry

    def _log_with_ai(self, message: str, context: str, level: str = "info"):
        entry = self.log(message, level)
        def _attach(commentary: str):
            entry["ai_commentary"] = commentary
        prompt = (
            "You are Monday, a smart home AI. Be concise (1-2 sentences max).\n"
            f"Context: {context}\n"
            f"Event: {message}\n"
            "Give a brief, helpful insight or recommendation for the homeowner."
        )
        _ollama_async(prompt, _attach)

    def check_ollama(self) -> bool:
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            self.ollama_available = resp.status_code == 200
        except Exception:
            self.ollama_available = False
        return self.ollama_available

    def process_event(self, event: SensorEvent):
        self.memory.add_short_term(event)
        current_hour = event.timestamp.hour

        if self.emergency.check_emergency(event):
            self.state = SystemState.EMERGENCY
            ctx = f"Sensor={event.sensor_type.value}, value={event.value:.2f}, location={event.location}"
            self._log_with_ai(
                f"[EMERGENCY] {event.sensor_type.value.upper()} at {event.location} = {event.value:.2f}",
                ctx, level="emergency"
            )
            return

        if self.state != SystemState.ACTIVE:
            if self.attention.should_wake_system(event, self.state, current_hour):
                self.log(f"[MONDAY] Waking from {self.state.value} — {event.sensor_type.value} spike ({event.value:.2f})")
                self.state = SystemState.ACTIVE
            else:
                self.log(f"[SLEEP] {event.sensor_type.value} = {event.value:.2f} — below threshold, staying in {self.state.value}")
                return

        self._dispatch(event)
        self._consider_sleep()

    def _dispatch(self, event: SensorEvent):

        if event.sensor_type == SensorType.MOTION:
            self._handle_motion(event)

        elif event.sensor_type == SensorType.POWER:
            self._handle_power(event)

        elif event.sensor_type in (
            SensorType.WIFI_PRESENCE,
            SensorType.BLUETOOTH_PRESENCE
        ):
            self._handle_presence(event)

        elif event.sensor_type == SensorType.LIGHT:
            self._handle_light(event)

        elif event.sensor_type == SensorType.TEMPERATURE:
            self._handle_temperature(event)

        elif event.sensor_type == SensorType.DOOR:
            self._handle_door(event)

        elif event.sensor_type == SensorType.GAS:
            self._handle_gas(event)

        elif event.sensor_type == SensorType.SMOKE:
            self._handle_smoke(event)

    def _handle_motion(self, event: SensorEvent):
        current_hour = event.timestamp.hour
        is_night     = Config.NIGHT_MODE_START_HOUR <= current_hour < Config.NIGHT_MODE_END_HOUR

        alert = self.anomaly.check_unexpected_motion(event, self.presence)
        if alert:
            self.notifications.send_notification("Security Alert", alert, priority="high")
            self._log_with_ai(f"[SECURITY] {alert}", f"night={is_night}, hour={current_hour}, distance={event.distance}", level="warning")

        if event.location in ("front_door", "back_door", "main_entrance"):
            threshold = Config.NIGHT_MOTION_DOOR_DISTANCE if is_night else Config.DAYTIME_MOTION_DOOR_DISTANCE
            if event.distance is not None and event.distance <= threshold:
                self.log(f"[DOOR] Close approach at {event.location} ({event.distance:.1f} m) → entry light ON")
                self.appliances.turn_on("lights_living_room", event.timestamp, self.log)
            else:
                dist_str = f"{event.distance:.1f} m" if event.distance else "unknown dist"
                self.log(f"[DOOR] Motion at {event.location} ({dist_str}) — too far, ignored")

        if event.location == "kitchen":
            self.appliances.turn_on("lights_kitchen", event.timestamp, self.log)
            if self.predictor.predict_coffee_machine_activation(event.timestamp, kitchen_motion_detected=True):
                self._log_with_ai(
                    "[MONDAY] Morning kitchen entry — pre-activating coffee machine",
                    f"avg_wake={self.memory.get_average_wake_time()}, hour={current_hour}",
                )
                self.appliances.turn_on("coffee_machine", event.timestamp, self.log)
                self.notifications.send_notification("Good Morning", "Coffee machine pre-activated", priority="info")
            if 4 <= current_hour <= 10:
                self.memory.record_habit("wake_up_times", current_hour + event.timestamp.minute / 60.0)

        if event.location == "living_room":
            self.appliances.turn_on("lights_living_room", event.timestamp, self.log)

        if event.location == "bedroom" and is_night and self.user_asleep:
            self.log("[MONDAY] Bedroom motion after sleep → marking user awake")
            self.user_asleep = False

    def _handle_power(self, event: SensorEvent):
        appliance = event.metadata.get("appliance")
        if not appliance:
            return
        warning = self.anomaly.check_power_anomaly(appliance, event.value)
        if warning:
            self.notifications.send_notification("Power Usage Warning", warning, priority="high")
            self._log_with_ai(f"[POWER ANOMALY] {warning}", f"appliance={appliance}, watts={event.value:.0f}", level="warning")
        else:
            self.log(f"[POWER] {appliance} drawing {event.value:.0f} W — normal")

    def _handle_presence(self, event: SensorEvent):
        wifi      = event.metadata.get("wifi", False)
        bluetooth = event.metadata.get("bluetooth", False)
        was_present = self.presence.user_present
        self.presence.update_presence(wifi, bluetooth, event.timestamp)

        if self.presence.user_present and not was_present:
            self._log_with_ai(
                f"[MONDAY] User arrived home at {event.timestamp.strftime('%H:%M')}",
                f"avg_arrival={self.memory.get_average_arrival_time()}, hour={event.timestamp.hour}",
            )
            self.memory.record_habit("home_arrival_times", event.timestamp.hour + event.timestamp.minute / 60.0)

        if not self.presence.user_present and was_present:
            self.log(f"[MONDAY] User left Wi-Fi/BT range at {event.timestamp.strftime('%H:%M')}")

        if not self.appliances.is_on("ac") and self.predictor.predict_ac_activation(event.timestamp):
            self._log_with_ai(
                "[MONDAY] Usual arrival time approaching — pre-activating AC",
                f"avg_arrival={self.memory.get_average_arrival_time()}",
            )
            self.appliances.turn_on("ac", event.timestamp, self.log)
            self.notifications.send_notification("AC Pre-Activated", "Home cooling before your usual arrival", priority="info")

        if not self.presence.user_present and self.appliances.is_on("ac"):
            absent_for = self.presence.get_absence_duration_minutes(event.timestamp)
            if absent_for >= Config.AC_AUTO_OFF_MINUTES:
                self.log(f"[MONDAY] User absent {absent_for:.0f} min → turning off AC")
                self.appliances.turn_off("ac", event.timestamp, self.memory, self.log)
                self.notifications.send_notification("AC Turned Off", f"AC off after {Config.AC_AUTO_OFF_MINUTES} min absence", priority="info")

    def _handle_light(self, event: SensorEvent):
        ambient    = event.value
        light_appl = f"lights_{event.location}"
        if light_appl not in self.appliances.appliance_states:
            return
        recent_motion = self.memory.get_recent_events(SensorType.MOTION, count=5)
        has_motion    = any(m.location == event.location for m in recent_motion)
        if ambient < 0.3 and has_motion:
            self.appliances.turn_on(light_appl, event.timestamp, self.log)
            self.log(f"[LIGHT] {event.location} dark ({ambient:.2f}) + motion → lights ON")
        elif ambient > 0.7:
            self.appliances.turn_off(light_appl, event.timestamp, self.memory, self.log)
            self.log(f"[LIGHT] {event.location} bright ({ambient:.2f}) → lights OFF")
        else:
            self.log(f"[LIGHT] {event.location} ambient={ambient:.2f}, no action")

    def _handle_temperature(self, event: SensorEvent):
        temp = event.value
        self.log(f"[TEMP] {event.location} = {temp:.1f}°C")
        if temp > 35:
            self._log_with_ai(
                f"[TEMP] High temperature at {event.location}: {temp:.1f}°C",
                f"ac_on={self.appliances.is_on('ac')}, user_present={self.presence.user_present}",
                level="warning"
            )
            if not self.appliances.is_on("ac") and self.presence.user_present:
                self.appliances.turn_on("ac", event.timestamp, self.log)
                self.notifications.send_notification("AC Auto-On", f"Temperature {temp:.1f}°C — AC activated", priority="high")
        elif temp < 16:
            self._log_with_ai(f"[TEMP] Low temperature: {temp:.1f}°C", f"user_present={self.presence.user_present}", level="info")

    def _handle_door(self, event: SensorEvent):
        state_str    = "OPENED" if event.value > 0.5 else "CLOSED"
        current_hour = event.timestamp.hour
        is_night     = Config.NIGHT_MODE_START_HOUR <= current_hour < Config.NIGHT_MODE_END_HOUR
        self.log(f"[DOOR] {event.location} {state_str}")
        if is_night and event.value > 0.5 and not self.presence.user_present:
            self._log_with_ai(
                f"[SECURITY] Door opened at night — {event.location}",
                f"hour={current_hour}, user_present=False",
                level="warning"
            )
            self.notifications.send_notification("Night Door Alert", f"{event.location} opened during night hours", priority="critical")

    def run_periodic_checks(self, current_time: datetime):
        self.predictor.reset_daily_flags(current_time)
        for appliance in self.appliances.appliance_states:
            rec = self.recommender.check_for_recommendation(appliance)
            if rec:
                self.notifications.send_recommendation_notification(rec)
                self.log(f"[REC] Suggested {rec['recommended_appliance']} for {rec['current_appliance']} (saves {rec['savings_percent']}%)")
        current_hour = current_time.hour
        if current_hour >= 23 or current_hour < 5:
            recent = self.memory.get_recent_events(SensorType.MOTION, count=3)
            if not recent:
                self.user_asleep = True

    def _consider_sleep(self):
        if self.state == SystemState.EMERGENCY:
            return
        if not any(self.appliances.appliance_states.values()):
            self.state = SystemState.LOW_POWER
            self.log("[MONDAY] No active appliances → low-power mode")

    def get_status_report(self) -> Dict:
        return {
            "system_state":       self.state.value,
            "user_present":       self.presence.user_present,
            "user_asleep":        self.user_asleep,
            "appliance_states":   dict(self.appliances.appliance_states),
            "total_power_watts":  self.appliances.get_total_power_draw(),
            "avg_wake_time":      self.memory.get_average_wake_time(),
            "avg_arrival_time":   self.memory.get_average_arrival_time(),
            "notifications_sent": len(self.notifications.notification_log),
            "ollama_available":   self.ollama_available,
            "event_log":          self.event_log[-50:],
            "notifications":      self.notifications.notification_log[-20:],
        }
    def _handle_gas(self, event: SensorEvent):

        gas_level = event.value

        self.log(
            f"[GAS] {event.location} = {gas_level:.2f}"
        )

        if gas_level > 0.4:

            self._log_with_ai(
                f"[GAS WARNING] Elevated gas detected in {event.location}",
                f"gas={gas_level}"
            )

            self.notifications.send_notification(
                "Gas Warning",
                f"Gas concentration increasing in {event.location}",
                priority="high"
            )

            self.appliances.turn_off(
                "coffee_machine",
                event.timestamp,
                self.memory,
                self.log
            )


    def _handle_smoke(self, event: SensorEvent):

        smoke = event.value

        self.log(
            f"[SMOKE] {event.location} = {smoke:.2f}"
        )

        if smoke > 0.3:

            self.notifications.send_notification(
                "Smoke Detected",
                f"Smoke detected in {event.location}",
                priority="critical"
            )

            self._log_with_ai(
                f"[SMOKE ALERT] Smoke in {event.location}",
                f"smoke={smoke}",
                level="warning"
            )