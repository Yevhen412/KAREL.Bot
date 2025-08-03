import asyncio
import datetime
import pytz
import os
from Run import run  # не меняем main.py

tz = pytz.timezone("Europe/Amsterdam")

async def scheduler():
    task = None
    while True:
        now = datetime.datetime.now(tz)
        hour = now.hour
        minute = now.minute

        # Старт в 08:00
        if hour == 8 and task is None:
            print("▶️ Автоматический запуск в 08:00 (по Нидерландам)")
            task = asyncio.create_task(main())

        # Остановка в 23:00
        elif hour == 23:
            print("🛑 Автоматическая остановка в 23:00 (по Нидерландам)")
            await asyncio.sleep(2)
            os._exit(0)

        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(scheduler())
