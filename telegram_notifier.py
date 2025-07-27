import os
import requests

# Безопасно получаем переменные
token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Проверка наличия переменных без их полного вывода
if not token or not chat_id:
    print("[!] Переменные окружения TELEGRAM_TOKEN или TELEGRAM_CHAT_ID не заданы.")
    print(f"TELEGRAM_TOKEN присутствует: {bool(token)}, длина: {len(token) if token else 0}")
    print(f"TELEGRAM_CHAT_ID присутствует: {bool(chat_id)}, длина: {len(chat_id) if chat_id else 0}")
else:
    print("[✓] Переменные окружения успешно загружены.")
    print(f"TELEGRAM_TOKEN (начало): {token[:5]}..., длина: {len(token)}")
    print(f"TELEGRAM_CHAT_ID (начало): {chat_id[:5]}..., длина: {len(chat_id)}")

def send_message(message: str):
    if not token or not chat_id:
        print("[!] Невозможно отправить сообщение — отсутствуют переменные окружения.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if not data.get("ok"):
            print(f"[✗] Ошибка при отправке в Telegram: {data}")
        else:
            print("[✓] Сообщение отправлено в Telegram.")
    except Exception as e:
        print(f"[!] Исключение при отправке сообщения в Telegram: {e}")
