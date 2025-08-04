import asyncio
import time
from ATR import calculate_atr
from Step import fetch_btc_candles, analyze_candle
from Deal import simulate_trade, report_hourly_pnl
from Telegram import send_telegram_message
from Start_stop import monitor_schedule  # ⬅️ Автостарт и автостоп по времени

btc_symbol = "BTCUSDT"

async def main():
    asyncio.create_task(monitor_schedule())  # ⏰ Запуск фонового мониторинга расписания

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
            send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")

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

        send_telegram_message("✅ Цикл завершён — ожидание следующей свечи")

if __name__ == "__main__":
    asyncio.run(main())
