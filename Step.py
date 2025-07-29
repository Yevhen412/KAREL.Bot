import aiohttp
import asyncio

BYBIT_URL = "https://api.bybit.com/v5/market/kline"

async def fetch_last_candle():
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "interval": "5",
        "limit": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BYBIT_URL, params=params) as resp:
            data = await resp.json()
            if data["retCode"] != 0:
                raise Exception("Failed to fetch candle data")
            return data["result"]["list"][0]

async def analyze_candle():
    candle = await fetch_last_candle()
    
    open_price = float(candle[1])
    high = float(candle[2])
    low = float(candle[3])
    close = float(candle[4])

    delta = high - low
    direction = "📈 Бычья" if close >= open_price else "📉 Медвежья"
    pct_change = ((close - open_price) / open_price) * 100

    return {
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "delta": delta,
        "direction": direction,
        "pct_change": pct_change
    }
