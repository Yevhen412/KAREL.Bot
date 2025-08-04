import aiohttp
import pandas as pd
import time

# Получаем исторические свечи по BTC (для ATR)
async def fetch_btc_candles(symbol="BTCUSDT", interval="5", limit=100):
    url = "https://api.bybit.com/v5/market/kline"
    category = "linear"
    end = int(time.time() * 1000)
    start = end - (limit * int(interval) * 60 * 1000)

    params = {
        "category": category,
        "symbol": symbol,
        "interval": interval,
        "start": start,
        "end": end,
        "limit": limit
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()

    if "result" not in data or "list" not in data["result"]:
        raise ValueError("❌ Ошибка получения данных BTC")

    df = pd.DataFrame(data["result"]["list"])
    df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df = df.astype({
        "open": float, "high": float, "low": float,
        "close": float, "volume": float
    })
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms")
    df.sort_values("timestamp", inplace=True)

    return df

# Анализ текущей 5-минутной свечи
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

            delta = abs(high_price - low_price)
            direction = "up" if close_price > open_price else "down"

            return delta, direction, close_price
