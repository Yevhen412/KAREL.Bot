import asyncio
from ATR import calculate_atr
from Step import analyze_candle
from Correlation import calculate_correlation
from AltFetcher import fetch_alt_candles

import datetime

async def main():
    print("\n=== RUNNING STRATEGY ===")

    # Получаем ATR BTC (по фьючерсам)
    atr_value = await calculate_atr()
    print(f"[{datetime.datetime.now()}] ✅ Current ATR (BTC): {atr_value:.2f}")

    # Получаем последнюю свечу BTC
    step_data = await get_latest_candle()
    if step_data is None:
        print("⚠️ Не удалось получить последнюю свечу.")
        return

    open_price = float(step_data["open"])
    close_price = float(step_data["close"])
    delta = abs(close_price - open_price)

    print(f"[{datetime.datetime.now()}] 📊 BTC Δ: {delta:.2f} / {atr_value:.2f} ATR")

    # Условие: если свеча прошла ≥ 50% ATR
    if delta >= 0.5 * atr_value:
        print(f"[{datetime.datetime.now()}] 🔍 Δ превышает 50% ATR → считаем корреляции...")

        target_symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT", "PEPEUSDT"]
        correlations = {}

        for symbol in target_symbols:
            alt_df = await fetch_alt_candles(symbol)
            corr = await calculate_correlation("BTCUSDT", alt_df)
            correlations[symbol] = corr

        print("\n📈 Коэффициенты корреляции:")
        for sym, val in correlations.items():
            print(f"{sym}: {val:.3f}")

    else:
        print(f"[{datetime.datetime.now()}] ❌ Δ ниже 50% ATR. Корреляции не считаем.")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
