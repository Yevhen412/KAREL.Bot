"""
import time
from datetime import datetime
from decimal import Decimal, getcontext
import requests

# БОльшая точность для денежных расчётов
getcontext().prec = 28

# ===== НАСТРОЙКИ =====
PAIR = "BTCUSDT"                      # Bybit USDT-перп (linear)
LEVERAGE = Decimal("3")               # плечо x3
TRADE_AMOUNT = Decimal("200")         # твоя изолированная маржа, USDT
TAKER_FEE = Decimal("0.001")          # 0.1% за сторону (вход и выход = 2 * 0.1%)
TARGET_NET_PROFIT = Decimal("0.01")   # чистыми +$0.01
POLL_PRICE_SEC = Decimal("0.2")       # частота опроса цены, когда позиция открыта
MAX_OPEN_PER_SEC = Decimal("1")       # не чаще 1 открытия в секунду

# ===== СОСТОЯНИЕ =====
in_position = False
last_open_ts = Decimal("0")
entry_price: Decimal | None = None
entry_time: datetime | None = None
required_exit_price: Decimal | None = None

# ===== УТИЛИТЫ =====
def get_current_price() -> Decimal | None:
    """Реальная последняя цена Bybit v5 для фьючерсов (linear)."""
    try:
        r = requests.get(
            "https://api.bybit.com/v5/market/tickers",
            params={"category": "linear", "symbol": PAIR},
            timeout=2
        )
        j = r.json()
        return Decimal(j["result"]["list"][0]["lastPrice"])
    except Exception as e:
        print(f"❌ Ошибка цены: {e}")
        return None

def notional() -> Decimal:
    """Нотиционал позиции (USDT)."""
    return TRADE_AMOUNT * LEVERAGE

def qty(entry_p: Decimal) -> Decimal:
    """Количество контрактов (BTC) = notional / entry_price."""
    return notional() / entry_p

def gross_pnl(entry_p: Decimal, exit_p: Decimal) -> Decimal:
    """Gross PnL = (exit - entry) * qty."""
    return (exit_p - entry_p) * qty(entry_p)

def total_fees() -> Decimal:
    """Суммарные комиссии за вход+выход как taker: notional * (fee_in + fee_out)."""
    return notional() * TAKER_FEE * 2

def net_pnl(entry_p: Decimal, exit_p: Decimal) -> Decimal:
    """Net PnL = Gross - Fees."""
    return gross_pnl(entry_p, exit_p) - total_fees()

def solve_required_exit_price(entry_p: Decimal) -> Decimal:
    """
    Находим минимальную цену выхода, при которой
    NET >= TARGET_NET_PROFIT (учтены две комиссии).
    NET = (p_exit - p_entry) * (notional / p_entry) - (notional * 2 * fee)
    => p_exit >= p_entry + (TARGET + notional*2*fee) * (p_entry / notional)
    """
    need_gross = TARGET_NET_PROFIT + total_fees()
    delta_price = need_gross / qty(entry_p)          # = need_gross * (entry_p / notional)
    return entry_p + delta_price

def is_margin_call(current_p: Decimal) -> bool:
    """
    Простейшая модель ликвидации (изолированная маржа):
    если нереализованный убыток по позиции <= -TRADE_AMOUNT, считаем margin call.
    (Процент ликвидации в реальности зависит от maintenance margin, но
     для симуляции этого достаточно.)
    """
    unrealized = gross_pnl(entry_price, current_p)
    return unrealized <= -TRADE_AMOUNT

def fmt(x: Decimal, n=2) -> str:
    return f"{x:.{n}f}"

def distance_to_target(cur: Decimal, target: Decimal) -> Decimal:
    return (target - cur) if target is not None else Decimal("0")

# ===== ТОРГОВАЯ ЛОГИКА =====
def open_trade_if_possible(now_ts: Decimal):
    global in_position, last_open_ts, entry_price, entry_time, required_exit_price
    if in_position:
        return
    if now_ts - last_open_ts < (Decimal("1") / MAX_OPEN_PER_SEC):
        return

    price = get_current_price()
    if price is None:
        return

    in_position = True
    last_open_ts = now_ts
    entry_price = price
    entry_time = datetime.now()
    required_exit_price = solve_required_exit_price(entry_price)

    # Отчёт по входу
    print(
        f"📥 ВХОД | {PAIR} | цена {fmt(entry_price)} | плечо x{LEVERAGE} | "
        f"цель (net +{TARGET_NET_PROFIT}): {fmt(required_exit_price)} | "
        f"время {entry_time.strftime('%H:%M:%S')}"
    )

def manage_open_trade():
    global in_position, entry_price, entry_time, required_exit_price
    if not in_position:
        return

    price = get_current_price()
    if price is None:
        return

    # Хартбит: сколько осталось до цели
    need = distance_to_target(price, required_exit_price)
    print(f"⏳ Цена {fmt(price)} | цель {fmt(required_exit_price)} | осталось {fmt(need)}")

    # TAKE PROFIT: строго только при достижении net >= +0.01
    if price >= required_exit_price:
        exit_price = price
        exit_time = datetime.now()
        g = gross_pnl(entry_price, exit_price)
        fees = total_fees()
        net = g - fees

        print(
            "✅ ВЫХОД (TAKE PROFIT)\n"
            f"Пара: {PAIR}\n"
            f"Вход:  {fmt(entry_price)}  ({entry_time.strftime('%H:%M:%S')})\n"
            f"Выход: {fmt(exit_price)}  ({exit_time.strftime('%H:%M:%S')})\n"
            f"Gross: {fmt(g, 5)} USDT | Комиссии: {fmt(fees, 5)} USDT | Net: {fmt(net, 5)} USDT"
        )

        # сброс состояния
        in_position = False
        entry_price = None
        entry_time = None
        required_exit_price = None
        return

    # MARGIN CALL (симулируем ликвидацию при потере всей маржи)
    if is_margin_call(price):
        exit_price = price
        exit_time = datetime.now()
        g = gross_pnl(entry_price, exit_price)
        fees = total_fees()
        net = g - fees

        print(
            "⚠️ MARGIN CALL (симуляция ликвидации)\n"
            f"Пара: {PAIR}\n"
            f"Вход:  {fmt(entry_price)}  ({entry_time.strftime('%H:%M:%S')})\n"
            f"Выход: {fmt(exit_price)}  ({exit_time.strftime('%H:%M:%S')})\n"
            f"Gross: {fmt(g, 5)} USDT | Комиссии: {fmt(fees, 5)} USDT | Net: {fmt(net, 5)} USDT"
        )

        # сброс состояния
        in_position = False
        entry_price = None
        entry_time = None
        required_exit_price = None
        return

# ===== MAIN =====
if __name__ == "__main__":
    print("📈 BTCUSDT Futures микроскальпер запущен (реальные цены, REST v5).")
    while True:
        now = Decimal(str(time.time()))
        open_trade_if_possible(now)   # вход не чаще 1/сек и только если нет позиции
        manage_open_trade()           # удерживаем до TP (net>=+0.01) или margin call
        time.sleep(float(POLL_PRICE_SEC if in_position else Decimal("1.0")))
