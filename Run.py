import asyncio
from ATR import fetch_btc_candles, calculate_atr
from Step import analyze_candle

async def main():
    candles_df = await fetch_btc_candles()
    atr = calculate_atr(candles_df)
    print(f"📏 ATR = {atr:.2f} USDT")

    condition_met, candle_data = await analyze_candle(atr)

    if condition_met:
        print("✅ Условие выполнено: свеча BTC прошла ≥ 50% ATR")
        # Здесь позже вызовем блок корреляции (блок 3)
    else:
        print("⏳ Условие не выполнено: свеча слабее 50% ATR")

if __name__ == "__main__":
    asyncio.run(main())
