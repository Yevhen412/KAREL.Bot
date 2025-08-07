import time
from decimal import Decimal
import requests

TRADE_AMOUNT = Decimal("200")
LEVERAGE = 3
TARGET_NET_PROFIT = Decimal("0.01")
TAKER_FEE = Decimal("0.001")
PAIR = "BTCUSDT"

def get_price():
    try:
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={PAIR}"
        r = requests.get(url, timeout=2)
        data = r.json()
        return Decimal(data["result"]["list"][0]["lastPrice"])
    except Exception as e:
        print("❌ Ошибка получения цены:", e)
        return None

def simulate():
    entry_price = get_price()
    if entry_price is None:
        return
    position_value = TRADE_AMOUNT * LEVERAGE
    fee = entry_price * position_value * TAKER_FEE * 2
    tp_price = entry_price + ((TARGET_NET_PROFIT + fee) / position_value)

    print(f"⏱️ Вход: {entry_price:.2f} → Жду 0.4 сек → Цель: {tp_price:.2f}")
    time.sleep(0.4)

    exit_price = get_price()
    if exit_price is None:
        return

    if exit_price >= tp_price:
        net = (exit_price - entry_price) * position_value - fee
        print(f"✅ Сделка: {entry_price:.2f} → {exit_price:.2f} | Чистыми: {net:.5f} USDT")
    else:
        print(f"❌ Не достигли цели. Сейчас: {exit_price:.2f}")

if __name__ == "__main__":
    while True:
        simulate()
        time.sleep(1)
