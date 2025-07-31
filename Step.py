import aiohttp
import pandas as pd

async def analyze_candle(df, atr_value):
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "interval": "5",
        "limit": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            kline = data['result']['list'][0]

            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])

            # Проверим на свечу без движения
            if high_price == low_price:
                print("[⚠️ WARNING] High == Low — свеча без движения. Пропуск анализа.")
                return 0.0, None

            delta = abs(high_price - low_price)
            pct_change = ((close_price - open_price) / open_price) * 100
            direction = "up" if close_price > open_price else "down"

            # Условие: если свеча прошла ≥ 50% ATR
            if delta >= 0.5 * atr_value:
                return delta, direction
            else:
                return delta, None
