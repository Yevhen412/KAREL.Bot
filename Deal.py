import asyncio
import aiohttp
from Telegram import send_telegram_message

total_pnl = 0  # Глобальный PnL за последний час

async def get_current_price():
    url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return float(data["result"]["list"][0]["lastPrice"])

async def simulate_trade(direction, entry_price, atr):
    global total_pnl

    tp_distance = 0.5 * atr
    sl_distance = 0.25 * atr

    if direction == "up":
        take_profit = entry_price + tp_distance
        stop_loss = entry_price - sl_distance
    else:
        take_profit = entry_price - tp_distance
        stop_loss = entry_price + sl_distance

    max_duration = 270  # максимум 4.5 минуты
    elapsed = 0
    pnl = 0
    result = "⏱ По времени"
    exit_price = entry_price

    while elapsed < max_duration:
        current_price = await get_current_price()

        if direction == "up":
            if current_price >= take_profit:
                pnl = take_profit - entry_price
                result = "✅ TP"
                exit_price = take_profit
                break
            elif current_price <= stop_loss:
                pnl = stop_loss - entry_price
                result = "🛑 SL"
                exit_price = stop_loss
                break

        else:  # direction == "down"
            if current_price <= take_profit:
                pnl = entry_price - take_profit
                result = "✅ TP"
                exit_price = take_profit
                break
            elif current_price >= stop_loss:
                pnl = entry_price - stop_loss
                result = "🛑 SL"
                exit_price = stop_loss
                break

        await asyncio.sleep(5)
        elapsed += 5

    if result == "⏱ По времени":
        current_price = await get_current_price()
        exit_price = current_price
        if direction == "up":
            pnl = current_price - entry_price
        else:
            pnl = entry_price - current_price

    total_pnl += pnl

    msg = (
        f"📤 {direction.upper()} | {result}\n"
        f"💰 PnL: {pnl:.2f} USDT"
    )
    send_telegram_message(msg)

async def report_hourly_pnl():
    global total_pnl
    msg = f"📊 Почасовой PnL: {total_pnl:.2f} USDT"
    send_telegram_message(msg)
    total_pnl = 0   
