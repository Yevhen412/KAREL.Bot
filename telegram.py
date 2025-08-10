# telegram.py
import time
from datetime import datetime
from typing import Optional
import requests

from config import (
    ENABLE_TELEGRAM,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    TG_RATE_LIMIT_SEC,
)

_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
_last_sent_ts: Optional[float] = None

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

def _send(text: str) -> None:
    """Отправка в Telegram с антирейтом. В консоль дублируем всегда."""
    global _last_sent_ts
    print(f"[{_ts()}] {text}")  # дублирование в консоль

    if not ENABLE_TELEGRAM or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    # защита от спама
    now = time.time()
    if _last_sent_ts is not None and (now - _last_sent_ts) < TG_RATE_LIMIT_SEC:
        return
    _last_sent_ts = now

    try:
        # ограничение TG: 4096 символов
        if len(text) > 4096:
            text = text[:4093] + "..."
        requests.post(
            _API_URL,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True},
            timeout=5,
        )
    except Exception as e:
        print(f"[{_ts()}] [TG ERROR] {e}")

def log(message: str) -> None:
    """Единый логгер: timestamp + сообщение (как раньше), но ещё и в Telegram."""
    _send(message)

# Дополнительно: удобные форматтеры событий (по желанию)
def log_entry(side: str, price: float, qty_btc: float):
    log(f"ENTRY FILLED: {side} @ {price:.1f} | qty={qty_btc:.6f} BTC")

def log_tp(price: float, move_pnl: float, fee: float, net: float):
    log(f"TP FILLED @ {price:.1f} | move_pnl={move_pnl:.4f} | fee={fee:.4f} | net={net:.4f}")

def log_sl(price: float, move_pnl: float, fee: float, net: float):
    log(f"SL MARKET @ {price:.1f} | move_pnl={move_pnl:.4f} | fee={fee:.4f} | net={net:.4f}")
