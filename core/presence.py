from datetime import datetime
from typing import Optional


class PresenceTracker:

    def __init__(self):
        self.user_present         = False
        self.last_seen:  Optional[datetime] = None
        self.last_absent_since: Optional[datetime] = None

    def update_presence(self, wifi_detected: bool, bluetooth_detected: bool, timestamp: datetime):
        previously_present = self.user_present

        # User is considered present if either signal is alive
        self.user_present = wifi_detected or bluetooth_detected

        if self.user_present:
            self.last_seen = timestamp
            self.last_absent_since = None
        else:
            if previously_present:
                # User just dropped off both signals, start the absence clock
                self.last_absent_since = timestamp

    def get_absence_duration_minutes(self, current_time: datetime) -> float:
        if self.user_present or self.last_absent_since is None:
            return 0.0
        delta = current_time - self.last_absent_since
        return delta.total_seconds() / 60.0