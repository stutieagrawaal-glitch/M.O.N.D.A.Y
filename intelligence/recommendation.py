from typing import Dict, List, Optional, Tuple

from config import Config
from core.memory import MemorySystem


class RecommendationEngine:

    def __init__(self, memory: MemorySystem):
        self.memory = memory

        # Simulated product database
        # In production this would call a REST API for up to date product data
        self.alternatives_database: Dict[str, List[Dict]] = {
            "coffee_machine": [
                {
                    "name":             "EcoBrew Pro X1",
                    "power_watts":      600,
                    "estimated_cost":   4500,
                    "brew_time_seconds": 45,
                    "savings_percent":  33,
                },
                {
                    "name":             "QuickJava Smart 200",
                    "power_watts":      550,
                    "estimated_cost":   5200,
                    "brew_time_seconds": 30,
                    "savings_percent":  38,
                },
            ],
            "ac": [
                {
                    "name":           "CoolTech Inverter V5",
                    "power_watts":    1000,
                    "estimated_cost": 35000,
                    "savings_percent": 33,
                },
            ],
            "water_heater": [
                {
                    "name":           "ThermoFlow Eco 2000",
                    "power_watts":    1500,
                    "estimated_cost": 8000,
                    "savings_percent": 25,
                },
            ],
        }

        # Track which appliances have already received a recommendation
        # so we do not notify the user repeatedly
        self.recommendations_sent: set = set()

    def check_for_recommendation(self, appliance: str) -> Optional[Dict]:
        # Skip if already recommended or no alternatives exist
        if appliance in self.recommendations_sent:
            return None
        if appliance not in self.alternatives_database:
            return None

        history = self.memory.habit_patterns["appliance_usage"].get(appliance, [])

        # Only recommend once there is meaningful usage history
        if len(history) < 5:
            return None

        current_baseline = Config.APPLIANCE_BASELINE_POWER.get(appliance, 0)
        alternatives     = self.alternatives_database[appliance]

        # Pick the alternative with the highest power saving
        best = max(alternatives, key=lambda a: a["savings_percent"])

        if best["power_watts"] < current_baseline:
            self.recommendations_sent.add(appliance)
            return {
                "current_appliance":       appliance,
                "current_power_watts":     current_baseline,
                "recommended_appliance":   best["name"],
                "recommended_power_watts": best["power_watts"],
                "savings_percent":         best["savings_percent"],
                "estimated_cost":          best["estimated_cost"],
                "usage_frequency":         len(history),
            }

        return None

    def get_most_used_appliances(self, top_n: int = 3) -> List[Tuple[str, int]]:
        counts = {
            appliance: len(sessions)
            for appliance, sessions in self.memory.habit_patterns["appliance_usage"].items()
        }
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]