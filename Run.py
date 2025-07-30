import asyncio
from ATR import fetch_btc_candles, calculate_atr
from Step import analyze_candle
from Correlation import calculate_correlation

async def main():
    print("=== RUNNING STRATEGY ===")

    # Получение свечей BTC
    df = await fetch_btc_candles()

    # Расчёт ATR
    atr_value = calculate_atr(df)
    print(f"ATR = {atr_value:.2f} USDT")

    # Анализ текущей 5-минутной свечи
    candle_passed_half_atr = await analyze_candle(df, atr_value)

    # Если свеча прошла более 50% ATR, запускаем расчёт корреляции
    if candle_passed_half_atr:
        print("Свеча превысила 50% ATR. Запуск расчёта корреляции...")
        await calculate_correlation()
    else:
        print("Свеча не превысила 50% ATR. Завершение.")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
