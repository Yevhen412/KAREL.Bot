import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Отсутствует TELEGRAM_TOKEN или TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Ошибка при отправке Telegram:", response.text)
    except Exception as e:
        print("Исключение при отправке Telegram:", e)
