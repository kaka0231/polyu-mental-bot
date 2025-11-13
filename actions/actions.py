from typing import Any, Text, Dict, List, Union
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
import logging
import os

logger = logging.getLogger(__name__)

# 生产环境不需要 dotenv
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

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

class ActionGenerateOpenRouterResponse(Action):  
    def name(self) -> Text:
        return "action_generate_deepseek_response" 

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # 检查 API key 是否存在
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not set in environment variables")
            dispatcher.utter_message(text="Service is temporarily unavailable. Please try again later.")
            return []

        user_message = tracker.latest_message.get('text', '')
        mood = tracker.get_slot("current_mood") or "neutral"
        history = tracker.events[-5:]

        # 安全检查
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

        # 历史记录摘要
        history_summary = []
        for e in history:
            if e.get('event') == 'user':
                history_summary.append(f"User: {e.get('text', '')[:50]}")
            elif e.get('event') == 'bot':
                history_summary.append(f"Bot: {e.get('text', '')[:50]}")
        history_summary = " | ".join(history_summary[-4:])

        user_prompt = f"Recent history: {history_summary}\nMood: {mood}\nUser: {user_message}\nSupportive response:"

        # OpenRouter API 调用
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://your-app.railway.app",  # 更新为你的 Railway URL
            "X-Title": "PolyU Mental Health Bot"
        }
        data = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        try:
            logger.info("Calling OpenRouter API...")
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            ai_reply = result["choices"][0]["message"]["content"].strip()
            logger.info(f"OpenRouter reply: {ai_reply[:100]}...")
            
            # 安全复查
            if any(kw in ai_reply.lower() for kw in harmful_keywords):
                ai_reply = "This sounds urgent—please call PolyU Counseling at 2766-6771 now. I'm here, but get pro help."
                return [SlotSet("needs_escalation", True), SlotSet("user_history", (tracker.get_slot("user_history") or []) + ["escalated"])]
            
            dispatcher.utter_message(text=ai_reply)
            return [SlotSet("user_history", (tracker.get_slot("user_history") or []) + [ai_reply[:50]])]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API error: {e} (Status: {getattr(e.response, 'status_code', 'N/A')})")
            dispatcher.utter_message(text="I'm having trouble connecting right now. Please try again in a moment.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            dispatcher.utter_message(text="I encountered an unexpected error. Please try rephrasing your question.")
            return []