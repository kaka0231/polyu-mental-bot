from typing import Any, Text, Dict, List, Union
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
import logging

logger = logging.getLogger(__name__)

# OpenRouter API Key (from openrouter.ai dashboard)
OPENROUTER_API_KEY = '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'  # Replace with your actual key

class ActionEscalateCrisis(Action):
    def name(self) -> Text:
        return "action_escalate_crisis"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_msg = tracker.latest_message.get('text', '')[:50]
        logger.warning(f"Crisis detected: Sender {tracker.sender_id}, msg: {user_msg}...")
        dispatcher.utter_message(text="Connecting you to immediate help—hold on.")
        return [SlotSet("needs_escalation", True), SlotSet("user_history", (tracker.get_slot("user_history") or []) + ["crisis_flag"])]

class ActionGenerateOpenRouterResponse(Action):  # Renamed for clarity
    def name(self) -> Text:
        return "action_generate_deepseek_response"  # Keep same name for Rasa compatibility

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_message = tracker.latest_message.get('text', '')
        mood = tracker.get_slot("current_mood") or "neutral"
        history = tracker.events[-5:]

        # Pre-check for crisis keywords (safety first)
        user_message_lower = user_message.lower()
        harmful_keywords = ['suicide', 'harm', 'kill', 'self my self']
        if any(kw in user_message_lower for kw in harmful_keywords):
            logger.warning(f"Crisis keyword detected: {user_message_lower}")
            dispatcher.utter_message(response="utter_crisis_escalate")
            return [SlotSet("needs_escalation", True), SlotSet("user_history", (tracker.get_slot("user_history") or []) + ["escalated"])]

        system_prompt = """
        You are a supportive mental health companion for PolyU university students. 
        Provide evidence-based CBT tips, encourage professional help if needed, 
        and respond warmly in English or Chinese. Do NOT diagnose or give medical advice. 
        If crisis (e.g., harm/suicide), escalate immediately. Keep responses short (2-4 sentences).
        """

        # History summary
        history_summary = []
        for e in history:
            if e.get('event') == 'user':
                history_summary.append(f"User: {e.get('text', '')[:50]}")
            elif e.get('event') == 'bot':
                history_summary.append(f"Bot: {e.get('text', '')[:50]}")
        history_summary = " | ".join(history_summary[-4:])

        user_prompt = f"Recent history: {history_summary}\nMood: {mood}\nUser: {user_message}\nSupportive response:"

        # OpenRouter API call (OpenAI-compatible)
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",  # Your site (optional, for attribution)
            "X-Title": "PolyU Mental Health Bot"  # Your app name (optional)
        }
        data = {
            "model": "openai/gpt-4o-mini",  # Free tier model; swap to "openai/gpt-4o" if needed
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 200  # Limit for cost/speed
        }
        
        try:
            logger.info("Calling OpenRouter API...")
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            ai_reply = result["choices"][0]["message"]["content"].strip()
            logger.info(f"OpenRouter reply: {ai_reply[:100]}...")
            
            # Safety: Re-check harmful content (extra layer)
            if any(kw in ai_reply.lower() for kw in harmful_keywords):
                ai_reply = "This sounds urgent—please call PolyU Counseling at 2766-6771 now. I'm here, but get pro help."
                return [SlotSet("needs_escalation", True), SlotSet("user_history", (tracker.get_slot("user_history") or []) + ["escalated"])]
            
            dispatcher.utter_message(text=ai_reply)
            return [SlotSet("user_history", (tracker.get_slot("user_history") or []) + [ai_reply[:50]])]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API error: {e} (Status: {getattr(e.response, 'status_code', 'N/A')})")
            dispatcher.utter_message(response="utter_api_error")  # Use your fallback
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            dispatcher.utter_message(response="utter_deepseek_fallback")
            return []