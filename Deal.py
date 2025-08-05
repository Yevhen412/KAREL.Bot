import asyncio
import aiohttp
from datetime import datetime
import pytz
from Telegram import send_telegram_message

# Общая прибыль за час
total_pnl = 0

# Размер сделки в USDT
deal_size = 200

# Получаем текущую цену BTC
async def get_current_price():
    url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return float(data["result"]["list"][0]["lastPrice"])

# Симуляция сделки
async def simulate_trade(direction, entry_price, atr):
    global total_pnl

    tp_distance = 0.5 * atr
    sl_distance = 0.25 * atr

    if direction == "up":
        take_profit = entry_price + tp_distance
        stop_loss = entry_price - sl_distance
        side = "BUY"
    else:
        take_profit = entry_price - tp_distance
        stop_loss = entry_price + sl_distance
        side = "SELL"

    tz = pytz.timezone("Europe/Amsterdam")
    open_time = datetime.now(tz).strftime("%H:%M:%S")

    max_duration = 270  # 4.5 минуты
    elapsed = 0

    while elapsed < max_duration:
        current_price = await get_current_price()

        if direction == "up":
            if current_price >= take_profit:
                exit_price = take_profit
                pnl = (exit_price - entry_price) * (deal_size / entry_price)
                total_pnl += pnl
                break
            elif current_price <= stop_loss:
                exit_price = stop_loss
                pnl = (exit_price - entry_price) * (deal_size / entry_price)
                total_pnl += pnl
                break
        else:
            if current_price <= take_profit:
                exit_price = take_profit
                pnl = (entry_price - exit_price) * (deal_size / entry_price)
                total_pnl += pnl
                break
            elif current_price >= stop_loss:
                exit_price = stop_loss
                pnl = (entry_price - exit_price) * (deal_size / entry_price)
                total_pnl += pnl
                break

        await asyncio.sleep(5)
        elapsed += 5

    else:
        # Время истекло — закрываем по текущей цене
        exit_price = await get_current_price()
        if direction == "up":
            pnl = (exit_price - entry_price) * (deal_size / entry_price)
        else:
            pnl = (entry_price - exit_price) * (deal_size / entry_price)
        total_pnl += pnl

    # Отправляем единое сообщение о сделке
    result_text = "ПРИБЫЛЬ" if pnl > 0 else "УБЫТОК"
    send_telegram_message(
        f"💼 {side} | {open_time}\n"
        f"▶️ Entry: {entry_price:.2f}\n"
        f"⏹ Exit: {exit_price:.2f}\n"
        f"💰 {result_text}: {pnl:.2f} USDT"
    )

# Отчёт каждый час
async def report_hourly_pnl():
    global total_pnl
    while True:
        await asyncio.sleep(3600)
        send_telegram_message(f"📊 Итог за последний час: {total_pnl:.2f} USDT")
        total_pnl = 0
