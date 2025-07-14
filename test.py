import asyncio
import json
from trade_simulator import TradeSimulator
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

simulator = TradeSimulator()
bot_active = True  # Состояние активности бота

@dp.message_handler(commands=['stop'])
async def stop_trading(message: types.Message):
    global bot_active
    bot_active = False
    await message.answer("⛔️ Бот остановлен. Сделки временно не обрабатываются.")

@dp.message_handler(commands=['start'])
async def start_trading(message: types.Message):
    global bot_active
    bot_active = True
    await message.answer("▶️ Бот снова активен и обрабатывает сигналы.")

async def main():
    async def handle_event(event):
        global bot_active
        if not bot_active:
            print("⏸ Бот остановлен. Сигнал пропущен.")
            return

        signal = simulator.process(event)
        if signal:
            result_msg = simulator.simulate_trade(signal)
            if result_msg:
                await bot.send_message(CHAT_ID, result_msg, parse_mode="HTML")

    while True:
        with open("sample_event.json") as f:
            event = json.load(f)
        await handle_event(event)
        await asyncio.sleep(5)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    executor.start_polling(dp)
