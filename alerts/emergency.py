from core.states import SensorEvent, SensorType
from config import Config
from alerts.notifications import NotificationSystem


class EmergencyHandler:

    def __init__(self, notification_system: NotificationSystem):
        self.notifications    = notification_system
        self.emergency_active = False

    def check_emergency(self, event: SensorEvent) -> bool:
        if event.sensor_type == SensorType.GAS and event.value >= Config.SPIKE_THRESHOLD_GAS:
            self._trigger("Gas Leak Detected", f"Gas sensor at {event.location} reading {event.value:.2f}")
            return True

        if event.sensor_type == SensorType.SMOKE and event.value >= Config.SPIKE_THRESHOLD_GAS:
            self._trigger("Smoke Detected", f"Smoke sensor at {event.location} reading {event.value:.2f}")
            return True

        return False

    def _trigger(self, title: str, message: str):
        self.emergency_active = True
        self.notifications.send_notification(title, message, priority="critical")

        print("\n[EMERGENCY PROTOCOL ACTIVATED]")
        print(f"   {title}")
        print("   Suggested actions: ventilate the area, shut off main gas valve, alert all occupants\n")

    def clear_emergency(self):
        self.emergency_active = False