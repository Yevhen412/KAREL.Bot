from ATR import fetch_btc_candles, calculate_atr
from Step import analyze_candle

async def main():
    btc_df = await fetch_btc_candles()
    atr_value = calculate_atr(btc_df)

    candle_data = await analyze_candle(atr_value)

    if candle_data:  # если свеча прошла 50% ATR
        print("Переход к блоку 3 — расчёт корреляции (ещё не реализован)")
    else:
        print("Свеча не прошла 50% ATR — ждём дальше")

import asyncio
asyncio.run(main())
