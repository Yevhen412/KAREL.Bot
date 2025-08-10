# utils.py
from datetime import datetime, timezone

def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def round_to_tick(price: float, tick: float) -> float:
    # округление вниз к ближайшему тик-ШАГУ
    return round((price // tick) * tick, 10)
