import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_message(text: str):
    """Отправка сообщения в Telegram (HTML). Без падений при ошибке."""
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ BOT_TOKEN или CHAT_ID не заданы — Telegram отключён")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=5,
        )
    except Exception as e:
        print(f"❌ Telegram error: {e}")
