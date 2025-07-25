import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta

# Настройки
symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT', 'ADAUSDT']
interval = '1'  # минутный таймфрейм
limit_per_request = 1000  # максимум за один запрос
days_back = 5

# Bybit REST API
base_url = 'https://api.bybit.com/v5/market/kline'

# Время
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=days_back)

def fetch_klines(symbol, start_ts, end_ts):
    df_all = []
    current_ts = start_ts

    print(f"⏳ Загружаем {symbol}...")

    while current_ts < end_ts:
        params = {
            'category': 'linear',
            'symbol': symbol,
            'interval': interval,
            'start': int(current_ts.timestamp() * 1000),
            'limit': limit_per_request,
        }
        try:
            response = requests.get(base_url, params=params, timeout=10)
            data = response.json()
            if data['retCode'] != 0 or not data['result']['list']:
                print(f"⚠️ Ошибка получения данных для {symbol}")
                break

            df = pd.DataFrame(data['result']['list'], columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df_all.append(df)

            # Следующий запрос — от последней метки времени
            last_ts = df['timestamp'].iloc[-1]
            current_ts = last_ts + timedelta(minutes=1)

            time.sleep(0.3)  # чтобы не перегрузить API

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            break

    if df_all:
        result = pd.concat(df_all, ignore_index=True)
        return result
    else:
        return pd.DataFrame()

# Создание папки, если нужно
if not os.path.exists("data"):
    os.makedirs("data")

# Загрузка и сохранение всех пар
for symbol in symbols:
    df = fetch_klines(symbol, start_time, end_time)
    if not df.empty:
        filename = f"data/{symbol}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Сохранено: {filename}")
    else:
        print(f"⚠️ Данные не получены: {symbol}")
