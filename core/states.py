from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class SystemState(Enum):
    DEEP_SLEEP = "deep_sleep"    # Ultra low power, only gas and smoke can wake
    LOW_POWER  = "low_power"     # Waiting for a spike, minimal processing
    ACTIVE     = "active"        # Fully awake, all modules running
    EMERGENCY  = "emergency"     # Gas or smoke detected, all actions locked to safety


class SensorType(Enum):
    MOTION              = "motion"
    DOOR                = "door"
    LIGHT               = "light"
    TEMPERATURE         = "temperature"
    POWER               = "power"
    GAS                 = "gas"
    SMOKE               = "smoke"
    WIFI_PRESENCE       = "wifi_presence"
    BLUETOOTH_PRESENCE  = "bluetooth_presence"


@dataclass
class SensorEvent:
    sensor_type: SensorType
    location:    str
    value:       float          # Normalised 0.0 to 1.0 for most sensors, watts for power events
    timestamp:   datetime
    distance:    Optional[float] = None          # Metres, used for motion events
    metadata:    Dict           = field(default_factory=dict)  # Flexible extra data per event type