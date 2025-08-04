import aiohttp
import pandas as pd
import time

async def calculate_atr(symbol="BTCUSDT", interval="5", length=12):
    url = "https://api.bybit.com/v5/market/kline"
    category = "linear"
    end = int(time.time() * 1000)
    start = end - (length * int(interval) * 60 * 1000)

    params = {
        "category": category,
        "symbol": symbol,
        "interval": interval,
        "start": start,
        "end": end,
        "limit": length
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()

    if "result" not in data or "list" not in data["result"]:
        raise ValueError("❌ Ошибка получения данных для ATR")

    df = pd.DataFrame(data["result"]["list"])
    df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
    df = df[["high", "low", "close"]].astype(float)

    df["prev_close"] = df["close"].shift(1)
    df["tr"] = df.apply(lambda row: max(
        row["high"] - row["low"],
        abs(row["high"] - row["prev_close"]),
        abs(row["low"] - row["prev_close"])
    ), axis=1)

    atr = df["tr"].rolling(window=length).mean().iloc[-1]
    return atr
