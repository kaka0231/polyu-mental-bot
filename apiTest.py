import requests
import json

# 你的 API Key（從 AIMLAPI 或 OpenRouter 獲取）
API_KEY = "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"  # 替換成 sk-xxx...

# API 端點（AIMLAPI 範例；OpenRouter 用 https://openrouter.ai/api/v1/chat/completions）
URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "gpt-4o",  # 或 "gpt-4o-mini" 免費更快
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, tell me a joke about AI."}
    ],
    "max_tokens": 100,  # 限制回應長度
    "temperature": 0.7  # 創造性
}

try:
    response = requests.post(URL, headers=headers, json=data)
    response.raise_for_status()  # 檢查 HTTP 錯誤
    
    result = response.json()
    ai_reply = result["choices"][0]["message"]["content"].strip()
    
    print("API Status:", response.status_code)
    print("GPT-4o Reply:", ai_reply)
    print("Usage:", result.get("usage", {}))  # Token 使用量
    
except requests.exceptions.RequestException as e:
    print("API Error:", e)
    if response.status_code == 401:
        print("提示：檢查 API Key 是否正確。")
    elif response.status_code == 402:
        print("提示：免費額度用完，充值或換平台。")
except KeyError:
    print("回應格式錯誤，請檢查 JSON。")
    print("Raw Response:", response.text)