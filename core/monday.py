import json
from datetime import datetime, timedelta
from typing import Dict

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


class Monday:

    def __init__(self):
        self.state      = SystemState.LOW_POWER
        self.memory     = MemorySystem()
        self.attention  = AttentionSystem()
        self.presence   = PresenceTracker()
        self.appliances = ApplianceController()
        self.predictor  = PredictionEngine(self.memory)
        self.anomaly    = AnomalyDetector(self.memory)
        self.recommender = RecommendationEngine(self.memory)
        self.notifications = NotificationSystem()
        self.emergency  = EmergencyHandler(self.notifications)

        # Whether the user has gone to sleep, used for night motion logic
        self.user_asleep = False

    # --------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------

    def log(self, message: str):
        print(message)

    # --------------------------------------------------------
    # MAIN EVENT ENTRY POINT
    # Every sensor reading comes through here
    # --------------------------------------------------------

    def process_event(self, event: SensorEvent):
        # Always record to short term memory regardless of system state
        self.memory.add_short_term(event)

        current_hour = event.timestamp.hour

        # Emergencies bypass the attention system entirely
        if self.emergency.check_emergency(event):
            self.state = SystemState.EMERGENCY
            return

        # Decide whether to wake up from low power mode
        if self.state != SystemState.ACTIVE:
            if self.attention.should_wake_system(event, self.state, current_hour):
                self.log(f"[MONDAY] Waking from {self.state.value} due to {event.sensor_type.value} spike")
                self.state = SystemState.ACTIVE
            else:
                return  # Stay asleep, ignore this event

        # Route to the correct handler
        self._dispatch(event)

        # After handling, check if Monday can return to low power
        self._consider_sleep()

    def _dispatch(self, event: SensorEvent):
        if event.sensor_type == SensorType.MOTION:
            self._handle_motion(event)
        elif event.sensor_type == SensorType.POWER:
            self._handle_power(event)
        elif event.sensor_type in (SensorType.WIFI_PRESENCE, SensorType.BLUETOOTH_PRESENCE):
            self._handle_presence(event)
        elif event.sensor_type == SensorType.LIGHT:
            self._handle_light(event)

    # --------------------------------------------------------
    # EVENT HANDLERS
    # --------------------------------------------------------

    def _handle_motion(self, event: SensorEvent):
        current_hour = event.timestamp.hour
        is_night = Config.NIGHT_MODE_START_HOUR <= current_hour < Config.NIGHT_MODE_END_HOUR

        # Outside motion during night hours at close range is a security alert
        alert = self.anomaly.check_unexpected_motion(event, self.presence)
        if alert:
            self.notifications.send_notification("Security Alert", alert, priority="high")

        # Door and entry point distance filtering
        # Prevents false triggers from distant vehicles or passersby
        if event.location in ("front_door", "back_door", "main_entrance"):
            threshold = Config.NIGHT_MOTION_DOOR_DISTANCE if is_night else Config.DAYTIME_MOTION_DOOR_DISTANCE
            if event.distance is not None and event.distance <= threshold:
                self.log(f"[DOOR] Close approach at {event.location} ({event.distance:.1f} m), activating entry light")
                self.appliances.turn_on("lights_living_room", event.timestamp, self.log)
            else:
                self.log(f"[DOOR] Motion at {event.location} ({event.distance:.1f} m), too far, ignored")

        # Kitchen motion triggers coffee machine prediction
        if event.location == "kitchen":
            self.appliances.turn_on("lights_kitchen", event.timestamp, self.log)

            if self.predictor.predict_coffee_machine_activation(event.timestamp, kitchen_motion_detected=True):
                self.log("[MONDAY] Morning kitchen entry detected, pre activating coffee machine")
                self.appliances.turn_on("coffee_machine", event.timestamp, self.log)
                self.notifications.send_notification(
                    "Good Morning",
                    "Coffee machine pre activated based on your usual morning routine",
                    priority="info",
                )

            # Record wake up time if motion is in the early morning window
            if 4 <= current_hour <= 10:
                self.memory.record_habit("wake_up_times", current_hour + event.timestamp.minute / 60.0)

        # Living room motion controls its light
        if event.location == "living_room":
            self.appliances.turn_on("lights_living_room", event.timestamp, self.log)

        # Bedroom movement after sleep marks the user as awake again
        if event.location == "bedroom" and is_night and self.user_asleep:
            self.log("[MONDAY] Bedroom motion after sleep, marking user as awake")
            self.user_asleep = False

    def _handle_power(self, event: SensorEvent):
        appliance = event.metadata.get("appliance")
        if not appliance:
            return
        warning = self.anomaly.check_power_anomaly(appliance, event.value)
        if warning:
            self.notifications.send_notification("Power Usage Warning", warning, priority="high")

    def _handle_presence(self, event: SensorEvent):
        wifi      = event.metadata.get("wifi", False)
        bluetooth = event.metadata.get("bluetooth", False)

        was_present = self.presence.user_present
        self.presence.update_presence(wifi, bluetooth, event.timestamp)

        # User just arrived home
        if self.presence.user_present and not was_present:
            self.log(f"[MONDAY] User arrived home at {event.timestamp.strftime('%H:%M')}")
            self.memory.record_habit("home_arrival_times", event.timestamp.hour + event.timestamp.minute / 60.0)

        # User just left range
        if not self.presence.user_present and was_present:
            self.log(f"[MONDAY] User left Wi Fi and Bluetooth range at {event.timestamp.strftime('%H:%M')}")

        # Pre activate AC if approaching usual arrival time and user is not home yet
        if not self.appliances.is_on("ac") and self.predictor.predict_ac_activation(event.timestamp):
            self.log("[MONDAY] Usual arrival time approaching, pre activating AC")
            self.appliances.turn_on("ac", event.timestamp, self.log)
            self.notifications.send_notification(
                "AC Pre Activated",
                "Your home is being cooled before your usual arrival time",
                priority="info",
            )

        # Auto off AC after user has been absent beyond the configured window
        if not self.presence.user_present and self.appliances.is_on("ac"):
            absent_for = self.presence.get_absence_duration_minutes(event.timestamp)
            if absent_for >= Config.AC_AUTO_OFF_MINUTES:
                self.log(f"[MONDAY] User absent {absent_for:.0f} min, turning off AC to save power")
                self.appliances.turn_off("ac", event.timestamp, self.memory, self.log)
                self.notifications.send_notification(
                    "AC Turned Off",
                    f"AC switched off automatically after {Config.AC_AUTO_OFF_MINUTES} minutes of your absence",
                    priority="info",
                )

    def _handle_light(self, event: SensorEvent):
        ambient = event.value  # 0.0 is dark, 1.0 is very bright
        light_appliance = f"lights_{event.location}"

        if light_appliance not in self.appliances.appliance_states:
            return

        recent_motion = self.memory.get_recent_events(SensorType.MOTION, count=5)
        location_has_recent_motion = any(m.location == event.location for m in recent_motion)

        if ambient < 0.3 and location_has_recent_motion:
            self.appliances.turn_on(light_appliance, event.timestamp, self.log)

        if ambient > 0.7:
            self.appliances.turn_off(light_appliance, event.timestamp, self.memory, self.log)

    # --------------------------------------------------------
    # PERIODIC CHECKS
    # Call this on a timer, for example every 5 minutes
    # --------------------------------------------------------

    def run_periodic_checks(self, current_time: datetime):
        self.predictor.reset_daily_flags(current_time)

        # Check if any frequently used appliance has a better alternative
        for appliance in self.appliances.appliance_states:
            rec = self.recommender.check_for_recommendation(appliance)
            if rec:
                self.notifications.send_recommendation_notification(rec)

        # Mark user as asleep during night hours if no recent motion
        current_hour = current_time.hour
        if current_hour >= 23 or current_hour < 5:
            recent = self.memory.get_recent_events(SensorType.MOTION, count=3)
            if not recent:
                self.user_asleep = True

    # --------------------------------------------------------
    # SLEEP MANAGEMENT
    # --------------------------------------------------------

    def _consider_sleep(self):
        if self.state == SystemState.EMERGENCY:
            return
        if not any(self.appliances.appliance_states.values()):
            self.state = SystemState.LOW_POWER
            self.log("[MONDAY] No active appliances, returning to low power mode")

    # --------------------------------------------------------
    # STATUS REPORT
    # --------------------------------------------------------

    def get_status_report(self) -> Dict:
        return {
            "system_state":        self.state.value,
            "user_present":        self.presence.user_present,
            "user_asleep":         self.user_asleep,
            "appliance_states":    dict(self.appliances.appliance_states),
            "total_power_watts":   self.appliances.get_total_power_draw(),
            "avg_wake_time":       self.memory.get_average_wake_time(),
            "avg_arrival_time":    self.memory.get_average_arrival_time(),
            "notifications_sent":  len(self.notifications.notification_log),
        }