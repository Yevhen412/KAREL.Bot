"""
ATR(48) по нефти (30-минутные бары) через IBKR API.

Что делает:
- Подключается к TWS/Gateway (Interactive Brokers).
- Резолвит Непрерывный фьючерс нефти: WTI (CL, NYMEX) или Brent (BZ, ICEEU/IPE).
- Загружает историю 30m-баров за указанный период (по умолчанию 10 D).
- Считает TR и ATR(48), печатает последнее значение и порог 25% ATR.
- Опционально сохраняет JSON-отчёт.

Запуск (пример):
    pip install ib-insync pandas pytz
    python atr_oil.py --instrument WTI --host 127.0.0.1 --port 7497 --clientId 11 --duration "10 D" --save /mnt/data/atr_oil_latest.json
"""

from __future__ import annotations

import os
import json
import argparse
from typing import Tuple

import pandas as pd
from ib_insync import IB, ContFuture, Future


def resolve_oil_contract(ib: IB, instrument: str) -> Tuple[object, str, str]:
    """
    Вернёт (qualifiedContract, symbol, exchange).
    instrument: 'WTI' или 'BRENT'.
    Сначала пытаемся взять Continuous Future (ContFuture).
    Если не удалось, падаем на ближайший обычный Future.
    """
    instrument = instrument.upper()
    if instrument not in {"WTI", "BRENT"}:
        raise ValueError("instrument должен быть 'WTI' или 'BRENT'")

    candidates = []
    if instrument == "WTI":
        candidates = [("CL", "NYMEX")]
    else:
        # Brent встречается как ICEEU или IPE
        candidates = [("BZ", "ICEEU"), ("BZ", "IPE")]

    last_err = None
    for sym, exch in candidates:
        # 1) Continuous
        try:
            cf = ContFuture(sym, exchange=exch)
            q = ib.qualifyContracts(cf)
            if q:
                return q[0], sym, exch
        except Exception as e:
            last_err = e
        # 2) Обычный front-month как fallback (пустой lastTradeDate берёт ближайший)
        try:
            f = Future(symbol=sym, exchange=exch, lastTradeDateOrContractMonth="")
            q = ib.qualifyContracts(f)
            if q:
                return q[0], sym, exch
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Не удалось зарезолвить контракт для {instrument}. Последняя ошибка: {last_err}")


def fetch_30m_bars(ib: IB, contract, duration: str = "10 D") -> pd.DataFrame:
    """
    Грузит 30-минутные бары. whatToShow='TRADES', useRTH=False.
    Возвращает DataFrame с колонками: ts, open, high, low, close, volume.
    """
    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting="30 mins",
        whatToShow="TRADES",
        useRTH=False,
        formatDate=1,
        keepUpToDate=False,
    )
    if not bars:
        raise RuntimeError("IBKR вернул пустой список баров. Проверь подписки на маркет-дату и права.")

    df = pd.DataFrame(
        [
            {
                "date": b.date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": getattr(b, "volume", None),
            }
            for b in bars
        ]
    )
    df["ts"] = pd.to_datetime(df["date"])
    df = df.drop(columns=["date"]).sort_values("ts").reset_index(drop=True)
    return df


def add_tr_atr(df: pd.DataFrame, atr_period: int = 48) -> pd.DataFrame:
    """
    Добавляет колонки:
      TR  = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
      ATR = SMA(TR, period)
    """
    prev_close = df["close"].shift(1)
    tr1 = (df["high"] - df["low"]).abs()
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df[f"ATR{atr_period}"] = df["TR"].rolling(atr_period, min_periods=atr_period).mean()
    return df


def print_separator():
    print("—" * 60)


def main():
    parser = argparse.ArgumentParser(description="ATR(48) по нефти через IBKR (30m)")
    parser.add_argument("--instrument", default=os.getenv("OIL_INSTRUMENT", "WTI"), choices=["WTI", "BRENT"])
    parser.add_argument("--host", default=os.getenv("IB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("IB_PORT", 7497)))
    parser.add_argument("--clientId", type=int, default=int(os.getenv("IB_CLIENT_ID", 11)))
    parser.add_argument("--duration", default=os.getenv("DURATION", "10 D"), help="Напр. '3 D', '2 W'")
    parser.add_argument("--save", default=os.getenv("ATR_SAVE", ""), help="Путь для JSON отчёта (опц.)")
    args = parser.parse_args()

    ib = IB()
    print(f"Подключение к IBKR {args.host}:{args.port} clientId={args.clientId} …")
    ib.connect(args.host, args.port, clientId=args.clientId)

    try:
        contract, sym, exch = resolve_oil_contract(ib, args.instrument)
        print(f"Контракт: {sym} @ {exch} (continuous или ближайший)")

        df = fetch_30m_bars(ib, contract, duration=args.duration)
        df = add_tr_atr(df, atr_period=48)

        last_row = df.dropna(subset=["ATR48"]).iloc[-1]
        atr48 = float(last_row["ATR48"])
        threshold = 0.25 * atr48

        print_separator()
        print(f"Последний бар: {last_row['ts']}")
        print(f"ATR(48) 30m: {atr48:.4f} USD")
        print(f"Порог 25% ATR: {threshold:.4f} USD")
        print_separator()

        if args.save:
            payload = {
                "instrument": args.instrument,
                "symbol": sym,
                "exchange": exch,
                "timestamp": str(last_row["ts"]),
                "atr48_30m_usd": atr48,
                "threshold_25pct_usd": threshold,
            }
            with open(args.save, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"JSON сохранён: {args.save}")

    finally:
        ib.disconnect()


if __name__ == "__main__":
    main()
