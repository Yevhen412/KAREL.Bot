import time
import requests
from decimal import Decimal
from Telegram import send_telegram_message

# === Константы ===
TRADE_AMOUNT = Decimal("200")
LEVERAGE = 3
TARGET_NET_PROFIT = Decimal("0.01")
TAKER_FEE = Decimal("0.001")  # 0.1%
PAIR = "BTCUSDT"

# === Глобальные переменные ===
last_trade_time = 0
in_trade = False

# === Получение текущей цены через REST ===
def get_current_price():
    url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={PAIR}"
    try:
        r = requests.get(url, timeout=2)
        data = r.json()
        price = Decimal(data["result"]["list"][0]["lastPrice"])
        return price
    except Exception as e:
        print("Ошибка при получении цены:", e)
        return None

# === Симуляция сделки ===
def simulate_trade(entry_price):
    global last_trade_time

    position_value = TRADE_AMOUNT * LEVERAGE
    target_profit = TARGET_NET_PROFIT
    total_fees = (entry_price * position_value) * TAKER_FEE * 2  # вход + выход

    required_exit_price = entry_price + ((target_profit + total_fees) / position_value)

    time.sleep(0.4)  # Имитируем ожидание выхода

    current_price = get_current_price()
    if current_price is None:
        return

    if current_price >= required_exit_price:
        net = (current_price - entry_price) * position_value - total_fees
        msg = (
            f"✅ Сделка завершена:\n"
            f"Пара: {PAIR}\n"
            f"Buy: {entry_price:.2f}\n"
            f"Sell: {current_price:.2f}\n"
            f"Net: {net:.5f} USDT"
        )
        print(msg)
        send_telegram_message(msg)

        last_trade_time = time.time()

# === Главный цикл стратегии ===
def run_micro_scalper():
    global in_trade, last_trade_time

    while True:
        now = time.time()
        if in_trade or now - last_trade_time < 1:
            time.sleep(0.1)
            continue

        entry_price = get_current_price()
        send_telegram_message(f"🔄 Цикл жив. Цена BTC: {entry_price}")
        if entry_price is None:
            continue

        in_trade = True
        simulate_trade(entry_price)
        in_trade = False
