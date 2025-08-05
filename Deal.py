import asyncio
import aiohttp
from Telegram import send_telegram_message

# Глобальный накопленный PnL
total_pnl = 0

# Размер сделки в долларах
deal_size = 200

async def get_current_price():
    url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            price = float(data["result"]["list"][0]["lastPrice"])
            return price

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

    send_telegram_message(
        f"📤 Сделка открыта: {direction.upper()} | Вход: {entry_price:.2f} | TP: {take_profit:.2f} | SL: {stop_loss:.2f}"
    )

    max_duration = 270  # 4.5 минуты
    elapsed = 0

    while elapsed < max_duration:
        current_price = await get_current_price()

        if direction == "up":
            if current_price >= take_profit:
                pnl = (take_profit - entry_price) * (deal_size / entry_price)
                total_pnl += pnl
                send_telegram_message(f"✅ TP достигнут | Прибыль: {pnl:.2f} USDT")
                return
            elif current_price <= stop_loss:
                pnl = (stop_loss - entry_price) * (deal_size / entry_price)
                total_pnl += pnl
                send_telegram_message(f"🛑 SL сработал | Убыток: {pnl:.2f} USDT")
                return

        else:  # direction == "down"
            if current_price <= take_profit:
                pnl = (entry_price - take_profit) * (deal_size / entry_price)
                total_pnl += pnl
                send_telegram_message(f"✅ TP достигнут | Прибыль: {pnl:.2f} USDT")
                return
            elif current_price >= stop_loss:
                pnl = (entry_price - stop_loss) * (deal_size / entry_price)
                total_pnl += pnl
                send_telegram_message(f"🛑 SL сработал | Убыток: {pnl:.2f} USDT")
                return

        await asyncio.sleep(5)
        elapsed += 5

    # Время истекло — фиксируем результат по текущей цене
    final_price = await get_current_price()
    if direction == "up":
        pnl = (final_price - entry_price) * (deal_size / entry_price)
    else:
        pnl = (entry_price - final_price) * (deal_size / entry_price)

    total_pnl += pnl
    status = "📉 Сделка закрыта по времени"
    result = "прибыль" if pnl > 0 else "убыток"
    send_telegram_message(f"{status} | {result}: {pnl:.2f} USDT")

async def report_hourly_pnl():
    global total_pnl
    while True:
        await asyncio.sleep(3600)
        send_telegram_message(f"🕒 Прибыль за последний час: {total_pnl:.2f} USDT")
        total_pnl = 0
