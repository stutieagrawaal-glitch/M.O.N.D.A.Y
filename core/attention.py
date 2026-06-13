from config import Config
from core.states import SensorEvent, SensorType, SystemState


class AttentionSystem:

    def __init__(self):
        # Static importance weight per sensor type
        # Gas and smoke are always 1.0 because they are life safety events
        # Other sensors get proportionally lower weights
        self.importance_weights = {
            SensorType.GAS:                  1.0,
            SensorType.SMOKE:                1.0,
            SensorType.DOOR:                 0.7,
            SensorType.MOTION:               0.6,
            SensorType.WIFI_PRESENCE:        0.5,
            SensorType.BLUETOOTH_PRESENCE:   0.5,
            SensorType.TEMPERATURE:          0.4,
            SensorType.POWER:                0.5,
            SensorType.LIGHT:                0.3,
        }

    def calculate_attention_score(
        self,
        event: SensorEvent,
        current_state: SystemState,
        current_hour: int,
    ) -> float:
        base_score = self.importance_weights.get(event.sensor_type, 0.3)

        # Multiply by sensor value so a faint reading has less weight
        score = base_score * event.value

        # Night time motion is escalated because unexpected movement is riskier
        if event.sensor_type == SensorType.MOTION:
            if Config.NIGHT_MODE_START_HOUR <= current_hour < Config.NIGHT_MODE_END_HOUR:
                score *= 1.5

        # Emergency sensors always score maximum, bypass all other logic
        if event.sensor_type in (SensorType.GAS, SensorType.SMOKE):
            return 1.0

        return min(score, 1.0)

    def should_wake_system(
        self,
        event: SensorEvent,
        current_state: SystemState,
        current_hour: int,
    ) -> bool:
        # Gas and smoke always wake the system immediately
        if event.sensor_type in (SensorType.GAS, SensorType.SMOKE):
            return True

        # Already active, no wake decision needed
        if current_state == SystemState.ACTIVE:
            return False

        score = self.calculate_attention_score(event, current_state, current_hour)
        return score >= Config.SPIKE_THRESHOLD_MOTION