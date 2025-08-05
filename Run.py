"""
import asyncio
import time
import pytz
from ATR import calculate_atr
from Step import fetch_btc_candles, analyze_candle
from Deal import simulate_trade, report_hourly_pnl
from Telegram import send_telegram_message
from Start_stop import monitor_schedule  # ⬅️ Автостарт и автостоп по времени
from datetime import datetime

def is_trading_hours():
    tz = pytz.timezone("Europe/Amsterdam")
    now = datetime.now(tz)
    return 8 <= now.hour < 23

btc_symbol = "BTCUSDT"

async def main():
    if not is_trading_hours():
        print("⏹ Вне торговых часов. Бот не запускается.")
        return

    asyncio.create_task(monitor_schedule())
    while True:
        try:
            # 📊 Ежечасный PnL-отчёт
            current_minute = time.localtime().tm_min
            if current_minute == 0:
                await report_hourly_pnl()
                await asyncio.sleep(60)  # Чтобы не дублировать в пределах одной минуты

            # ⏳ Ждём открытия новой свечи
            now = time.time()
            wait = 300 - (now % 300)
            await asyncio.sleep(wait)

            # 🟡 Получаем ATR
            btc_atr = await calculate_atr()

            # 👁 Наблюдение за свечой
            while True:
                btc_df = await fetch_btc_candles()
                delta, direction, price = await analyze_candle(btc_df, btc_atr)

                if delta >= 0.25 * btc_atr:
                    await simulate_trade(direction, price, btc_atr)
                    break
                else:
                    await asyncio.sleep(10)

        except Exception as e:
            send_telegram_message(f"❌ Ошибка в основном цикле: {e}")

if __name__ == "__main__":
    asyncio.run(main())
