import os
import aiohttp

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def test_send():
    print("BOT_TOKEN:", BOT_TOKEN)
    print("CHAT_ID:", CHAT_ID)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': 'Test message from Railway'}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            print("Status:", resp.status)
            print("Response:", await resp.text())
