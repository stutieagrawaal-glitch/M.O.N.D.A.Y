from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from core.states import SensorEvent, SensorType


class MemorySystem:

    def __init__(self):
        # Short term rolling buffer, one deque per sensor type
        self.short_term_memory: Dict[SensorType, deque] = defaultdict(
            lambda: deque(maxlen=Config.SHORT_TERM_MEMORY_SIZE)
        )

        # Long term memory keyed by date string, then by label
        # Example: long_term_memory["2024-06-14"]["kitchen_first_motion"] = 6.5
        self.long_term_memory: Dict[str, Dict] = {}

        # Habit patterns learned from repeated observations
        # Lists grow to LONG_TERM_MEMORY_DAYS length then drop oldest entries
        self.habit_patterns: Dict = {
            "wake_up_times":       [],   # Hour as float, 6.5 means 6 30 AM
            "kitchen_after_wake":  [],
            "home_arrival_times":  [],   # Hour as float
            "sleep_times":         [],
            "appliance_usage":     defaultdict(list),
        }

    # --------------------------------------------------------
    # SHORT TERM
    # --------------------------------------------------------

    def add_short_term(self, event: SensorEvent):
        self.short_term_memory[event.sensor_type].append(event)

    def get_recent_events(self, sensor_type: SensorType, count: int = 10) -> List[SensorEvent]:
        memory = self.short_term_memory[sensor_type]
        return list(memory)[-count:]

    # --------------------------------------------------------
    # LONG TERM KEY VALUE STORE
    # --------------------------------------------------------

    def store_long_term(self, date_key: str, key: str, value):
        if date_key not in self.long_term_memory:
            self.long_term_memory[date_key] = {}
        self.long_term_memory[date_key][key] = value

    def get_long_term(self, date_key: str, key: str, default=None):
        return self.long_term_memory.get(date_key, {}).get(key, default)

    # --------------------------------------------------------
    # HABIT RECORDING
    # --------------------------------------------------------

    def record_habit(self, habit_type: str, value):
        if habit_type not in self.habit_patterns:
            return
        target = self.habit_patterns[habit_type]
        if isinstance(target, list):
            target.append(value)
            if len(target) > Config.LONG_TERM_MEMORY_DAYS:
                target.pop(0)

    def record_appliance_usage(
        self,
        appliance: str,
        duration_minutes: float,
        power_used: float,
        timestamp: datetime,
    ):
        self.habit_patterns["appliance_usage"][appliance].append({
            "duration_minutes": duration_minutes,
            "power_used":       power_used,
            "timestamp":        timestamp,
            "hour_of_day":      timestamp.hour,
        })

    # --------------------------------------------------------
    # AVERAGES USED BY PREDICTION ENGINE
    # --------------------------------------------------------

    def get_average_wake_time(self) -> Optional[float]:
        times = self.habit_patterns["wake_up_times"]
        if not times:
            return None
        return sum(times) / len(times)

    def get_average_arrival_time(self) -> Optional[float]:
        times = self.habit_patterns["home_arrival_times"]
        if not times:
            return None
        return sum(times) / len(times)