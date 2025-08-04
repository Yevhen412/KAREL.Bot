import asyncio
import time
from ATR import calculate_atr
from Step import fetch_btc_candles, analyze_candle
from Deal import simulate_trade
from Telegram import send_telegram_message
from Start_stop import monitor_schedule  # ⏰ проверка торгового времени

btc_symbol = "BTCUSDT"

async def main():
    while True:
        try:
            # ⏰ Проверка времени
            if not is_trading_hours():
                send_telegram_message("⏸ Вне торгового окна (23:00–08:00 по NL). Ожидаем 08:00...")
                await asyncio.sleep(600)
                continue

            # ⌛ Ждём начала новой свечи
            now = time.time()
            wait = 300 - (now % 300)
            send_telegram_message(f"⏳ Ждём открытия новой свечи: {int(wait)} сек...")
            await asyncio.sleep(wait)

            # 1. Расчёт ATR
            btc_atr = await calculate_atr()
            send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")

            # 2. Мониторинг текущей свечи
            entry_triggered = False
            direction = None
            entry_price = None
            delta = 0

            while True:
                btc_df = await fetch_btc_candles()
                delta, direction, current_price = await analyze_candle(btc_df, btc_atr)

                if delta >= 0.25 * btc_atr and not entry_triggered:
                    entry_triggered = True
                    entry_price = current_price
                    tp = entry_price + 0.5 * btc_atr if direction == "up" else entry_price - 0.5 * btc_atr
                    sl = entry_price - 0.25 * btc_atr if direction == "up" else entry_price + 0.25 * btc_atr
                    simulate_trade(direction, entry_price, tp, sl)
                    send_telegram_message(
                        f"📈 Сделка открыта по BTC\nΔ: {delta:.2f}\nDirection: {direction.upper()}\n"
                        f"Entry: {entry_price:.2f}\nTP: {tp:.2f}\nSL: {sl:.2f}"
                    )
                    break  # Завершаем цикл — ждём новую свечу
                else:
                    await asyncio.sleep(10)

        except Exception as e:
            send_telegram_message(f"❌ Ошибка в основном цикле: {e}")

        send_telegram_message("✅ Цикл завершён — ожидаем следующую 5-мин свечу")

if __name__ == "__main__":
    asyncio.run(main())
