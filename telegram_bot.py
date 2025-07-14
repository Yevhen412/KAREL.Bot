import os
import aiohttp
import asyncio
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MY_CHAT_ID")
BOT_ENABLE = os.getenv("BOT_ENABLE", "true").lower() == "true"

# === Новый флаг для ручного управления ===
IS_ACTIVE = True
last_message_time = datetime.min

async def notify_telegram(message):
    global last_message_time

    if not BOT_ENABLE or not IS_ACTIVE:
        print("🔕 Telegram notifications are disabled.")
        return

    # === Ограничение по частоте: 1 сообщение/сек ===
    if (datetime.now() - last_message_time).total_seconds() < 1:
        await asyncio.sleep(1)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                text = await resp.text()
                if resp.status == 429:
                    # === Обработка ошибки Telegram 429 ===
                    retry_after = int(eval(text).get("parameters", {}).get("retry_after", 5))
                    print(f"⚠️ Too many requests, sleeping {retry_after}s")
                    await asyncio.sleep(retry_after)
                else:
                    print(f"✅ Telegram response: {resp.status} - {text}")
                last_message_time = datetime.now()
    except Exception as e:
        print(f"Telegram send error: {e}")

# === Команды управления из Telegram (/pause и /resume) ===
async def handle_command(text):
    global IS_ACTIVE
    if text == "/pause":
        IS_ACTIVE = False
        await notify_telegram("⏸️ Бот остановлен вручную.")
    elif text == "/resume":
        IS_ACTIVE = True
        await notify_telegram("▶️ Бот возобновлён вручную.")
