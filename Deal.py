"""
import time
from datetime import datetime
from decimal import Decimal, getcontext
import requests

# Повышаем точность для денежных расчётов
getcontext().prec = 28

# ====== НАСТРОЙКИ ======
PAIR = "BTCUSDT"                  # Bybit USDT-фьючерс
LEVERAGE = Decimal("3")           # плечо
TRADE_AMOUNT = Decimal("200")     # из собственных средств, USDT (изолированная маржа)
TAKER_FEE = Decimal("0.001")      # 0.1% на вход и 0.1% на выход (taker)
TARGET_NET_PROFIT = Decimal("0.01")  # ЧИСТАЯ цель (+0.01 USDT)
POLL_PRICE_SEC = 0.2              # как часто опрашивать цену, когда позиция открыта
MAX_OPEN_PER_SEC = 1              # не более 1 открытия в секунду

# ====== ГЛОБАЛЬНОЕ СОСТОЯНИЕ ======
in_position = False
last_open_ts = 0.0
entry_price: Decimal | None = None
entry_time: datetime | None = None
required_exit_price: Decimal | None = None  # цена, дающая net >= +0.01 после комиссий

# ====== УТИЛИТЫ ======
def get_current_price() -> Decimal | None:
    """
    Реальная последняя цена с Bybit v5 (фьючерсный рынок / linear).
    """
    url = "https://api.bybit.com/v5/market/tickers"
    try:
        r = requests.get(url, params={"category": "linear", "symbol": PAIR}, timeout=2)
        j = r.json()
        # ожидаем структуру {"result":{"list":[{"lastPrice":"..."}]}}
        price = Decimal(j["result"]["list"][0]["lastPrice"])
        return price
    except Exception as e:
        print(f"❌ Ошибка цены: {e}")
        return None

def position_value() -> Decimal:
    """Нотионал позиции с учётом плеча."""
    return TRADE_AMOUNT * LEVERAGE  # USDT

def total_fees(entry_p: Decimal, exit_p: Decimal | None = None) -> Decimal:
    """
    Комиссия биржи считается от нотиционала сделки (price*qty = notional).
    Берём «по-простому»: per side = notional * fee; всего два раза (вход+выход).
    """
    notional = position_value()
    # если выход ещё не известен — всё равно комиссии одинаковы (notional одинаковый)
    return notional * TAKER_FEE * 2

def gross_pnl(entry_p: Decimal, exit_p: Decimal) -> Decimal:
    """
    Реальный PnL для USDT-маржин фьючерса (linear):
    PnL = (exit - entry) * qty, где qty = notional / entry.
    """
    notional = position_value()
    qty = notional / entry_p
    return (exit_p - entry_p) * qty

def net_pnl(entry_p: Decimal, exit_p: Decimal) -> Decimal:
    """Чистая прибыль после двух комиссий."""
    return gross_pnl(entry_p, exit_p) - total_fees(entry_p, exit_p)

def solve_required_exit_price(entry_p: Decimal) -> Decimal:
    """
    Найдём цену выхода, при которой NET >= TARGET_NET_PROFIT.
    NET = (p_exit - p_entry) * (notional / p_entry) - (notional * fee * 2)
    => p_exit >= p_entry + (TARGET + notional*fee*2) * (p_entry / notional)
    """
    notional = position_value()
    add = (TARGET_NET_PROFIT + (notional * TAKER_FEE * 2)) * (entry_p / notional)
    return entry_p + add

def is_margin_call(current_p: Decimal) -> bool:
    """
    Простейшая модель маржин-колла при изолированной марже:
    если нереализованный убыток по позиции <= -TRADE_AMOUNT (вся собственная маржа),
    считаем, что произошёл margin call.
    """
    unrealized = gross_pnl(entry_price, current_p)
    return unrealized <= -TRADE_AMOUNT

def fmt(x: Decimal, n=2) -> str:
    return f"{x:.{n}f}"

def safe_send_telegram(text: str):
    """
    Если у тебя есть Telegram.py с send_telegram_message, раскомментируй:
    from Telegram import send_telegram_message
    и зови её здесь. Сейчас — тихий no-op.
    """
    try:
        from Telegram import send_telegram_message
        send_telegram_message(text)
    except Exception:
        pass

# ====== ТОРГОВАЯ ЛОГИКА ======
def open_trade_if_possible(now_ts: float):
    global in_position, last_open_ts, entry_price, entry_time, required_exit_price
    if in_position:
        return
    # лимит на открытия: не чаще 1 в секунду
    if now_ts - last_open_ts < (1 / MAX_OPEN_PER_SEC):
        return

    price = get_current_price()
    if price is None:
        return

    in_position = True
    last_open_ts = now_ts
    entry_price = price
    entry_time = datetime.now()
    required_exit_price = solve_required_exit_price(entry_price)

    log = (
        f"📥 ВХОД | {PAIR} | цена {fmt(entry_price)} | плечо x{LEVERAGE} | "
        f"цель (net +{TARGET_NET_PROFIT} USDT): {fmt(required_exit_price)} | "
        f"время {entry_time.strftime('%H:%M:%S')}"
    )
    print(log)
    safe_send_telegram(log)

def manage_open_trade():
    """
    Если позиция открыта — следим за ценой до достижения TP (net>=+0.01)
    или до маржин-колла. Позиция живёт сколько нужно.
    """
    global in_position, entry_price, entry_time, required_exit_price

    if not in_position:
        return

    price = get_current_price()
    if price is None:
        return

    # TP?
    if price >= required_exit_price:
        exit_price = price
        exit_time = datetime.now()
        net = net_pnl(entry_price, exit_price)
        gross = gross_pnl(entry_price, exit_price)

        msg = (
            "✅ ВЫХОД (TAKE PROFIT)\n"
            f"Пара: {PAIR}\n"
            f"Вход: {fmt(entry_price)}  ({entry_time.strftime('%H:%M:%S')})\n"
            f"Выход: {fmt(exit_price)}  ({exit_time.strftime('%H:%M:%S')})\n"
            f"Gross PnL: {fmt(gross, 5)} USDT\n"
            f"Комиссии: {fmt(total_fees(entry_price), 5)} USDT\n"
            f"Net PnL: {fmt(net, 5)} USDT"
        )
        print(msg)
        safe_send_telegram(msg)

        # сброс состояния
        in_position = False
        entry_price = None
        entry_time = None
        required_exit_price = None
        return

    # Margin Call?
    if is_margin_call(price):
        exit_price = price
        exit_time = datetime.now()
        net = net_pnl(entry_price, exit_price)
        gross = gross_pnl(entry_price, exit_price)

        msg = (
            "⚠️ MARGIN CALL (симуляция ликвидации)\n"
            f"Пара: {PAIR}\n"
            f"Вход: {fmt(entry_price)}  ({entry_time.strftime('%H:%M:%S')})\n"
            f"Выход: {fmt(exit_price)}  ({exit_time.strftime('%H:%M:%S')})\n"
            f"Gross PnL: {fmt(gross, 5)} USDT\n"
            f"Комиссии (включены в Net при закрытии): {fmt(total_fees(entry_price), 5)} USDT\n"
            f"Net PnL: {fmt(net, 5)} USDT"
        )
        print(msg)
        safe_send_telegram(msg)

        # сброс состояния
        in_position = False
        entry_price = None
        entry_time = None
        required_exit_price = None
        return

    # Отладочный heartbeat (можно закомментировать)
    print(f"⏳ Ожидание... текущая {fmt(price)} | цель {fmt(required_exit_price)}")

# ====== MAIN LOOP ======
if __name__ == "__main__":
    print("📈 BTCUSDT Futures микроскальпер (симулятор) запущен.")
    while True:
        now = time.time()
        # 1) пытаемся открыть позицию (если нет)
        open_trade_if_possible(now)
        # 2) если уже открыта — ведём её до TP или margin call
        manage_open_trade()
        # Пауза опроса: когда позиция открыта — чаще, когда нет — реже
        time.sleep(POLL_PRICE_SEC if in_position else 1.0)
