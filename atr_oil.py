from future import annotations 
import os 
import json 
import argparse 
from typing import Optional, Tuple
import pandas as pd 
from ib_insync import IB, ContFuture

def resolve_oil_contract(ib: IB, instrument: str) -> Tuple[object, str, str]: """Вернёт (qualifiedContract, symbol, exchange). instrument: 'WTI' или 'BRENT'. """ instrument = instrument.upper() if instrument not in {"WTI", "BRENT"}: raise ValueError("instrument должен быть WTI или BRENT")

trials = []
if instrument == "WTI":
    trials = [("CL", "NYMEX")]
else:  # BRENT
    # Порядок попыток: ICEEU -> IPE (некоторые аккаунты видят IPE)
    trials = [("BZ", "ICEEU"), ("BZ", "IPE")]

last_err = None
for sym, exch in trials:
    try:
        cf = ContFuture(sym, exchange=exch)
        q = ib.qualifyContracts(cf)
        if q:
            return q[0], sym, exch
    except Exception as e:
        last_err = e
raise RuntimeError(f"Не удалось зарезолвить контракт для {instrument}. Последняя ошибка: {last_err}")

def fetch_30m_bars(ib: IB, contract, duration: str = "10 D") -> pd.DataFrame: bars = ib.reqHistoricalData( contract, endDateTime="", durationStr=duration, barSizeSetting="30 mins", whatToShow="TRADES", useRTH=False, formatDate=1, keepUpToDate=False, ) if not bars: raise RuntimeError("IB вернул пустой список баров. Проверьте маркет-дата подписки и права на инструмент.")

df = pd.DataFrame([{
    "date": b.date,
    "open": b.open,
    "high": b.high,
    "low": b.low,
    "close": b.close,
    "volume": getattr(b, "volume", None),
} for b in bars])

# Преобразуем дату в pandas datetime (таймзона IB может быть локальной для контракта; для ATR это не критично)
df["ts"] = pd.to_datetime(df["date"])  # оставляем naive
df = df.drop(columns=["date"]).sort_values("ts").reset_index(drop=True)
return df

def add_tr_atr(df: pd.DataFrame, atr_period: int = 48) -> pd.DataFrame: """Добавляет колонки TR и ATR(atr_period).""" close_shift = df["close"].shift(1) tr1 = (df["high"] - df["low"]).abs() tr2 = (df["high"] - close_shift).abs() tr3 = (df["low"] - close_shift).abs() df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1) df[f"ATR{atr_period}"] = df["TR"].rolling(atr_period, min_periods=atr_period).mean() return df

def main(): parser = argparse.ArgumentParser(description="ATR(48) по нефти через IBKR") parser.add_argument("--instrument", default=os.getenv("OIL_INSTRUMENT", "WTI"), choices=["WTI", "BRENT"], help="Нефть: WTI или BRENT") parser.add_argument("--host", default=os.getenv("IB_HOST", "127.0.0.1")) parser.add_argument("--port", type=int, default=int(os.getenv("IB_PORT", 7497))) parser.add_argument("--clientId", type=int, default=int(os.getenv("IB_CLIENT_ID", 11))) parser.add_argument("--duration", default=os.getenv("DURATION", "10 D"), help="Длительность истории, например '3 D', '2 W'") parser.add_argument("--save", default=os.getenv("ATR_SAVE", ""), help="Путь для JSON отчёта (опционально)") args = parser.parse_args()

ib = IB()
print(f"Подключение к IBKR {args.host}:{args.port} clientId={args.clientId} …")
ib.connect(args.host, args.port, clientId=args.clientId)

try:
    contract, sym, exch = resolve_oil_contract(ib, args.instrument)
    print(f"Контракт: {sym} @ {exch} (continuous future)")

    df = fetch_30m_bars(ib, contract, duration=args.duration)
    df = add_tr_atr(df, atr_period=48)

    last = df.dropna(subset=["ATR48"]).iloc[-1]
    atr48 = float(last["ATR48"])
    threshold = 0.25 * atr48

    print("—" * 60)
    print(f"Последний бар: {last['ts']}")
    print(f"ATR(48) (30m): {atr48:.4f} USD")
    print(f"Порог 25% ATR: {threshold:.4f} USD")
    print("—" * 60)

    if args.save:
        payload = {
            "instrument": args.instrument,
            "symbol": sym,
            "exchange": exch,
            "timestamp": str(last["ts"]),
            "atr48_30m_usd": atr48,
            "threshold_25pct_usd": threshold,
        }
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"JSON сохранён: {args.save}")

finally:
    ib.disconnect()

if name == "main": main()

