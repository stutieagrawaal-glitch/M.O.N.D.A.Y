# Simulates hardware sensor readings for testing Monday on a desktop
# On a real Raspberry Pi, replace these methods with actual GPIO reads
from datetime import datetime, timedelta

from core.states import SensorEvent, SensorType


class SensorSimulator:

    def __init__(self):
        self.simulated_time = datetime.now()

    def advance_time(self, minutes: int = 1) -> datetime:
        self.simulated_time += timedelta(minutes=minutes)
        return self.simulated_time

    def generate_motion_event(self, location: str, distance: float, intensity: float) -> SensorEvent:
        return SensorEvent(
            sensor_type=SensorType.MOTION,
            location=location,
            value=intensity,
            timestamp=self.simulated_time,
            distance=distance,
        )

    def generate_power_event(self, appliance: str, watts: float) -> SensorEvent:
        return SensorEvent(
            sensor_type=SensorType.POWER,
            location="home",
            value=watts,
            timestamp=self.simulated_time,
            metadata={"appliance": appliance},
        )

    def generate_gas_event(self, location: str, gas_level: float) -> SensorEvent:
        return SensorEvent(
            sensor_type=SensorType.GAS,
            location=location,
            value=gas_level,
            timestamp=self.simulated_time,
        )

    def generate_smoke_event(self, location: str, smoke_level: float) -> SensorEvent:
        return SensorEvent(
            sensor_type=SensorType.SMOKE,
            location=location,
            value=smoke_level,
            timestamp=self.simulated_time,
        )

    def generate_presence_event(self, wifi: bool, bluetooth: bool) -> SensorEvent:
        return SensorEvent(
            sensor_type=SensorType.WIFI_PRESENCE,
            location="home",
            value=1.0 if (wifi or bluetooth) else 0.0,
            timestamp=self.simulated_time,
            metadata={"wifi": wifi, "bluetooth": bluetooth},
        )

    def generate_light_event(self, location: str, ambient_level: float) -> SensorEvent:
        # ambient_level: 0.0 is fully dark, 1.0 is bright daylight
        return SensorEvent(
            sensor_type=SensorType.LIGHT,
            location=location,
            value=ambient_level,
            timestamp=self.simulated_time,
        )