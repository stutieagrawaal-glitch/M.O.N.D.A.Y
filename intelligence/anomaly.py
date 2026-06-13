from datetime import datetime
from typing import Optional

from config import Config
from core.memory import MemorySystem
from core.presence import PresenceTracker
from core.states import SensorEvent


class AnomalyDetector:

    def __init__(self, memory: MemorySystem):
        self.memory = memory

    def check_power_anomaly(self, appliance: str, current_power_watts: float) -> Optional[str]:
        history = self.memory.habit_patterns["appliance_usage"].get(appliance, [])

        # Need at least a few sessions to establish a baseline average
        if len(history) < 3:
            return None

        past_values = [entry["power_used"] for entry in history[-10:]]
        average     = sum(past_values) / len(past_values)

        if average == 0:
            return None

        if current_power_watts > average * Config.POWER_ANOMALY_MULTIPLIER:
            return (
                f"WARNING: {appliance.replace('_', ' ')} is drawing {current_power_watts:.0f} watts, "
                f"significantly above its usual average of {average:.0f} watts. "
                f"Check if the appliance is faulty or was left on accidentally."
            )

        return None

    def check_unexpected_motion(
        self,
        event: SensorEvent,
        presence: PresenceTracker,
    ) -> Optional[str]:
        current_hour = event.timestamp.hour
        is_night     = Config.NIGHT_MODE_START_HOUR <= current_hour < Config.NIGHT_MODE_END_HOUR

        if (
            is_night
            and event.location == "outside"
            and event.distance is not None
            and event.distance <= Config.NIGHT_MOTION_OUTSIDE_DISTANCE
        ):
            return (
                f"Motion detected outside at {event.distance:.1f} m "
                f"at {event.timestamp.strftime('%H:%M:%S')} during night hours. "
                f"Please verify this is not an intruder."
            )

        return None