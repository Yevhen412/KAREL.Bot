# telegram.py
import os
import time
import requests
from datetime import datetime
from config import ENABLE_TELEGRAM, TG_RATE_LIMIT_SEC

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

_last_send_time = 0

def log(message: str):
    """Отправка сообщения в Telegram (с защитой от спама)."""
    global _last_send_time
    now_time = time.time()
    if not ENABLE_TELEGRAM or not TOKEN or not CHAT_ID:
        return

    # защита от спама
    if now_time - _last_send_time < TG_RATE_LIMIT_SEC:
        return

    timestamp = datetime.now().strftime("%H:%M:%S")
    text = f"[{timestamp}] {message}"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}

    try:
        requests.post(url, data=payload)
        _last_send_time = now_time
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
