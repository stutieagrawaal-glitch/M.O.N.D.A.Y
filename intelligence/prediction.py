from datetime import datetime
from typing import Optional

from config import Config
from core.memory import MemorySystem


class PredictionEngine:

    def __init__(self, memory: MemorySystem):
        self.memory = memory

        # Daily flags prevent the same prediction firing multiple times in one day
        self.coffee_pre_activated_today = False
        self.ac_pre_activated_today     = False
        self.last_reset_date            = None

    def reset_daily_flags(self, current_time: datetime):
        today = current_time.date()
        if self.last_reset_date != today:
            self.coffee_pre_activated_today = False
            self.ac_pre_activated_today     = False
            self.last_reset_date            = today

    def predict_coffee_machine_activation(
        self,
        current_time: datetime,
        kitchen_motion_detected: bool,
    ) -> bool:
        avg_wake = self.memory.get_average_wake_time()
        if avg_wake is None or self.coffee_pre_activated_today:
            return False

        current_decimal = current_time.hour + current_time.minute / 60.0

        # Trigger if kitchen motion happens within 30 minutes of the average wake time
        if kitchen_motion_detected and abs(current_decimal - avg_wake) <= 0.5:
            self.coffee_pre_activated_today = True
            return True

        return False

    def predict_ac_activation(self, current_time: datetime) -> bool:
        avg_arrival = self.memory.get_average_arrival_time()
        if avg_arrival is None or self.ac_pre_activated_today:
            return False

        current_decimal   = current_time.hour + current_time.minute / 60.0
        pre_activate_time = avg_arrival - (Config.AC_PRE_ACTIVATION_MINUTES / 60.0)

        # Fire once when the current time enters the pre activation window
        if pre_activate_time <= current_decimal < avg_arrival:
            self.ac_pre_activated_today = True
            return True

        return False