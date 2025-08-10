# utils.py
from datetime import datetime

def format_price(price: float, decimals: int = 2) -> str:
    """Форматирует цену с указанным количеством знаков."""
    return f"{price:.{decimals}f}"

def format_usd(amount: float, decimals: int = 2) -> str:
    """Форматирует сумму в USD."""
    return f"${amount:.{decimals}f}"

def ts_to_str(ts: float) -> str:
    """Преобразует timestamp в строку формата ЧЧ:ММ:СС."""
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")

def calc_take_profit(entry_price: float, tp_usd: float) -> float:
    """Рассчитывает цену тейк-профита от цены входа."""
    return entry_price + tp_usd

def calc_stop_loss(entry_price: float, sl_usd: float) -> float:
    """Рассчитывает цену стоп-лосса от цены входа."""
    return entry_price - sl_usd
