import asyncio
from ATR import fetch_btc_candles, calculate_atr
from Step import analyze_candle

async def main():
    # Получаем данные свечей и ATR из блока 1
    candles_df = await fetch_btc_candles()
    atr = calculate_atr(candles_df)

    print("📏 ATR за 12 свечей (5m):")
    print(f"ATR = {atr:.2f} USDT\n")

    # Получаем данные текущей свечи из блока 2
    candle_data = await analyze_candle()

    print("🕯 Данные последней свечи BTC (5m):")
    print(f"Открытие: {candle_data['open']}")
    print(f"Максимум: {candle_data['high']}")
    print(f"Минимум: {candle_data['low']}")
    print(f"Закрытие: {candle_data['close']}")
    print(f"Дельта (High - Low): {candle_data['delta']:.2f}")
    print(f"Направление: {candle_data['direction']}")
    print(f"Изменение за свечу: {candle_data['pct_change']:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
