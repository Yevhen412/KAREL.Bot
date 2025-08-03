import asyncio
import os
import pytz
from datetime import datetime
from Telegram import send_telegram_message

async def monitor_schedule():
    tz = pytz.timezone("Europe/Amsterdam")
    notified_start = False
    notified_stop = False

    while True:
        now = datetime.now(tz)
        hour = now.hour

        # Уведомление в 08:00
        if hour == 8 and not notified_start:
            await send_telegram_message("▶️ Сессия автоматически возобновлена в 08:00.")
            notified_start = True
            notified_stop = False

        # Остановка в 23:00
        elif hour == 23 and not notified_stop:
            await send_telegram_message("⏹ Контейнер остановлен по расписанию в 23:00.")
            await asyncio.sleep(2)  # Дать время Telegram
            os._exit(0)

        await asyncio.sleep(60)
