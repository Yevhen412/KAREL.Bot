import os
import aiohttp

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def notify_telegram(message: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram not configured")
        return

    print(f"Sending to Telegram with token: {BOT_TOKEN}, chat_id: {CHAT_ID}")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"Failed to send message: {resp.status} — {text}")
                else:
        print("Telegram message sent successfully")
        
    except Exception as e:
        print(f"Telegram error: {e}")
