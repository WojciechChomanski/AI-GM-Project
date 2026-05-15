import requests
import logging

logger = logging.getLogger(__name__)

class ChatAPIClient:
    def __init__(self, api_url="http://127.0.0.1:8000/chat"):
        self.api_url = api_url

    def get_response(self, npc_name, player_input):
        try:
            payload = {"npc": npc_name, "player_input": player_input}
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            return response.json().get("reply", f"{npc_name} remains silent.")
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return f"⚠️ Error in dialogue: {e}"