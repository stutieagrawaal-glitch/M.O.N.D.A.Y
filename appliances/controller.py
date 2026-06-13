# appliances/controller.py
# Manages the physical state of every appliance in the home
# Tracks power draw, on/off state, and session duration
# Records completed sessions to memory for later analysis

import random
from datetime import datetime
from typing import Dict, Optional


class ApplianceController:

    def __init__(self):
        # Current on/off state for each managed appliance
        self.appliance_states: Dict[str, bool] = {
            "coffee_machine":      False,
            "ac":                  False,
            "lights_living_room":  False,
            "lights_kitchen":      False,
            "lights_bedroom":      False,
            "tv":                  False,
            "water_heater":        False,
        }

        # Timestamp when each appliance was last turned on
        self.appliance_on_time: Dict[str, Optional[datetime]] = {
            name: None for name in self.appliance_states
        }

        # Simulated current power draw in watts
        # On a real Pi this would come from a current sensor such as SCT 013
        self.current_power_draw: Dict[str, float] = {
            name: 0.0 for name in self.appliance_states
        }

        # Baseline watts per appliance used for simulation
        from config import Config
        self._baseline = Config.APPLIANCE_BASELINE_POWER

    def turn_on(self, appliance: str, timestamp: datetime, log_callback=None):
        if appliance not in self.appliance_states:
            return
        if self.appliance_states[appliance]:
            return  # Already on, do nothing

        self.appliance_states[appliance] = True
        self.appliance_on_time[appliance] = timestamp

        # Simulate real world variance in power draw around the baseline
        baseline = self._baseline.get(appliance, 100)
        self.current_power_draw[appliance] = baseline * random.uniform(0.95, 1.05)

        if log_callback:
            log_callback(f"[APPLIANCE] {appliance.replace('_', ' ').upper()} turned ON at {timestamp.strftime('%H:%M:%S')}")

    def turn_off(self, appliance: str, timestamp: datetime, memory, log_callback=None):
        if appliance not in self.appliance_states:
            return
        if not self.appliance_states[appliance]:
            return  # Already off, do nothing

        # Record this session before clearing the state
        on_time = self.appliance_on_time[appliance]
        if on_time and memory:
            duration_minutes = (timestamp - on_time).total_seconds() / 60.0
            # Energy used in watt hours = watts * hours
            energy_wh = self.current_power_draw[appliance] * (duration_minutes / 60.0)
            memory.record_appliance_usage(appliance, duration_minutes, energy_wh, on_time)

        self.appliance_states[appliance] = False
        self.appliance_on_time[appliance] = None
        self.current_power_draw[appliance] = 0.0

        if log_callback:
            log_callback(f"[APPLIANCE] {appliance.replace('_', ' ').upper()} turned OFF at {timestamp.strftime('%H:%M:%S')}")

    def is_on(self, appliance: str) -> bool:
        return self.appliance_states.get(appliance, False)

    def get_total_power_draw(self) -> float:
        return sum(self.current_power_draw.values())