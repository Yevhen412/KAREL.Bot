import os
import asyncio
import pandas as pd
import datetime
from bybit_api import fetch_ohlcv
from correlation import compute_correlation
from notifier import send_message

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT", "ADAUSDT"]
TIMEFRAME = "5"
DAYS = 1
CORR_THRESHOLD = 0.85
CHECK_INTERVAL = 60  # сек между проверками (по умолчанию каждую минуту)
ALERT_INTERVAL = 600  # если нет импульса, напоминание "бот жив" каждые 10 минут

async def main_loop():
    last_alert_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=ALERT_INTERVAL)

    while True:
        now_nl = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        if now_nl.hour >= 0 and now_nl.hour < 7:
            await send_message("⏸ Бот остановлен: ночь (00:00–07:00 NL времени).")
            while True:
                await asyncio.sleep(60)
                now_nl = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                if now_nl.hour == 7 and now_nl.minute == 0:
                    await send_message("▶️ Бот возобновлён в 07:00 (NL время).")
                    break

        try:
            dfs = {}
            for pair in PAIRS:
                df = await fetch_ohlcv(pair, TIMEFRAME, DAYS)
                dfs[pair] = df

            btc_df = dfs["BTCUSDT"]
            btc_range = btc_df["high"].iloc[-1] - btc_df["low"].iloc[-1]
            atr = btc_df["high"].sub(btc_df["low"]).rolling(window=14).mean().iloc[-1]

            if btc_range >= 0.5 * atr:
                report = f"⚡️ BTC движение: {btc_range:.2f} (ATR: {atr:.2f})\n"
                for pair, df in dfs.items():
                    if pair == "BTCUSDT":
                        continue
                    corr = compute_correlation(btc_df, df)
                    if corr >= CORR_THRESHOLD:
                        delta = df["high"].iloc[-1] - df["low"].iloc[-1]
                        pct = 100 * delta / df["low"].iloc[-1]
                        report += f"🔗 {pair}: корреляция {corr:.2f}, Δ {pct:.2f}%\n"
                await send_message(report)
                last_alert_time = datetime.datetime.utcnow()

            # напоминание, что бот жив (если нет импульса)
            if (datetime.datetime.utcnow() - last_alert_time).total_seconds() >= ALERT_INTERVAL:
                await send_message("🤖 Бот активен, импульсов пока нет.")
                last_alert_time = datetime.datetime.utcnow()

        except Exception as e:
            await send_message(f"❗️ Ошибка: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main_loop())
