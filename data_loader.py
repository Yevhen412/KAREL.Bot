# data_loader.py
import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
from datetime import datetime, timedelta
import time

# === Настройка API (можно будет вынести в переменные окружения) ===
api_key = ""
api_secret = ""
session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

# === Функция загрузки данных по символам ===
def load_data(symbols, interval="1", limit=360):
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - limit * 60 * 1000  # в миллисекундах

    all_data = {}
    for symbol in symbols:
        try:
            print(f"Загружаем {symbol}...")
            res = session.get_kline(
                category="spot",
                symbol=symbol,
                interval=interval,
                start=start_time,
                end=end_time
            )
            data = res['result']['list']
            df = pd.DataFrame(data, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
            df["close"] = df["close"].astype(float)
            df = df[["timestamp", "close"]].set_index("timestamp")
            all_data[symbol] = df
            time.sleep(0.25)
        except Exception as e:
            print(f"Ошибка загрузки {symbol}: {e}")

    # Объединение в один DataFrame
    merged = pd.concat(all_data.values(), axis=1)
    merged.columns = symbols
    merged.dropna(inplace=True)
    return merged
    
