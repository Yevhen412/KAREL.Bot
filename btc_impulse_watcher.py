import requests
import pandas as pd
import asyncio
import datetime
import time
import os

# === Telegram токен и ID (из Railway Variables) ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === НАСТРОЙКИ ===
SYMBOL = "BTCUSDT"
PAIRS_TO_ANALYZE = ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT", "ADAUSDT"]
INTERVAL = "5"
ATR_PERIOD = 14
ATR_MULTIPLIER = 0.5
CHECK_INTERVAL = 300  # каждые 5 минут
ALIVE_NOTIFICATION_INTERVAL = 1800  # каждые 30 минут

last_alive_notification = time.time()

# === Отправка Telegram-сообщений ===
async def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print("Ошибка при отправке в Telegram:", e)

# === ЗАГРУЗКА ДАННЫХ С BYBIT ===
def fetch_data(symbol):
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": 100
    }
    res = requests.get(url, params=params).json()
    kline = res["result"]["list"]
    df = pd.DataFrame(kline, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "turnover"
    ])
    df = df.astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df

# === РАСЧЁТ ATR ===
def calculate_atr(df):
    df["H-L"] = df["high"] - df["low"]
    df["H-PC"] = abs(df["high"] - df["close"].shift(1))
    df["L-PC"] = abs(df["low"] - df["close"].shift(1))
    tr = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    atr = tr.rolling(window=ATR_PERIOD).mean()
    return atr.iloc[-1]

# === РАСЧЁТ КОРРЕЛЯЦИИ ===
async def analyze_correlation(btc_df):
    msg = "<b>📊 Корреляция с BTC:</b>\n"
    btc_returns = btc_df["close"].pct_change()

    for pair in PAIRS_TO_ANALYZE:
        try:
            alt_df = fetch_data(pair)
            alt_returns = alt_df["close"].pct_change()
            corr = btc_returns.corr(alt_returns)

            # Изменение монеты в % за последнюю свечу
            price_diff = alt_df["close"].iloc[-1] - alt_df["open"].iloc[-1]
            pct_change = (price_diff / alt_df["open"].iloc[-1]) * 100

            msg += (
                f"🔸 <b>{pair}</b>\n"
                f"Корреляция: {corr:.3f}\n"
                f"Движение: {pct_change:.2f}%\n\n"
            )
        except Exception as e:
            msg += f"⚠ Ошибка по {pair}: {str(e)}\n"

    await send_telegram_message(msg)

# === ПРОВЕРКА BTC ===
async def check_btc_movement():
    global last_alive_notification

    try:
        btc_df = fetch_data(SYMBOL)
        atr = calculate_atr(btc_df)

        recent_high = btc_df["high"].iloc[-1]
        recent_low = btc_df["low"].iloc[-1]
        recent_change = recent_high - recent_low
        close_prev = btc_df["close"].iloc[-2]
        pct_change = (recent_change / close_prev) * 100
        timestamp = datetime.datetime.utcnow().strftime('%H:%M:%S')

        if recent_change >= atr * ATR_MULTIPLIER:
            msg = (
                f"🚨 <b>Импульс BTC!</b>\n"
                f"Время (UTC): {timestamp}\n"
                f"Размах свечи: {recent_change:.2f} USDT ({pct_change:.2f}%)\n"
                f"ATR({ATR_PERIOD}) = {atr:.2f}\n"
                f"➡ Проверяем корреляции..."
            )
            await send_telegram_message(msg)

            await analyze_correlation(btc_df)

        elif time.time() - last_alive_notification > ALIVE_NOTIFICATION_INTERVAL:
            await send_telegram_message(f"✅ Бот активен. Нет импульсов. Время: {timestamp}")
            last_alive_notification = time.time()

    except Exception as e:
        await send_telegram_message(f"❌ Ошибка в watcher:\n{str(e)}")

# === ЗАПУСК БОТА ===
async def main():
    while True:
        await check_btc_movement()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
