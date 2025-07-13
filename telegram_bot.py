import os
import aiohttp

if os.getenv("BOT_ENABLED", "true") != "true":
    print("Bot is paused via BOT_ENABLED")
    exit()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MY_CHAT_ID")

async def notify_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                print(f"Telegram response: {resp.status} - {await resp.text()}")
    except Exception as e:
        print(f"Telegram send error: {e}")
