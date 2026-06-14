from datetime import datetime
from typing import Dict, List


class NotificationSystem:

    def __init__(self):
        self.notification_log: List[Dict] = []

    def send_notification(self, title: str, message: str, priority: str = "normal"):
        entry = {
            "title":     title,
            "message":   message,
            "priority":  priority,
            "timestamp": datetime.now(),
        }
        self.notification_log.append(entry)

        # Console output simulates what would be a push notification
        print(f"\n[PHONE NOTIFICATION] [{priority.upper()}] {title}")
        print(f"   {message}\n")

        # Real hardware implementation would do something like:
        # requests.post("https://api.telegram.org/bot<TOKEN>/sendMessage",
        #               json={"chat_id": CHAT_ID, "text": f"{title}\n{message}"})

    def send_recommendation_notification(self, recommendation: Dict):
        appliance = recommendation["current_appliance"].replace("_", " ")
        title     = "Energy Saving Suggestion"
        message   = (
            f"You use the {appliance} frequently "
            f"({recommendation['usage_frequency']} sessions recorded). "
            f"The {recommendation['recommended_appliance']} uses "
            f"{recommendation['recommended_power_watts']} W instead of "
            f"{recommendation['current_power_watts']} W, saving around "
            f"{recommendation['savings_percent']}% on power. "
            f"Estimated price: {recommendation['estimated_cost']} rupees."
        )
        self.send_notification(title, message, priority="info")
