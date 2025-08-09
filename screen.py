
import os
import time
import json
import asyncio
import random
from typing import Optional, Tuple, List

import websockets
import httpx

from telegram import send_message
import deal


# ========= НАСТРОЙКИ =========
HELIUS_API_KEY      = os.getenv("HELIUS_API_KEY")
PUMPFUN_PROGRAM_ID  = os.getenv("PUMPFUN_PROGRAM_ID")
USER_PUBKEY         = os.getenv("USER_PUBKEY")

MAX_TOKEN_AGE_SEC   = int(os.getenv("MAX_TOKEN_AGE_SEC", "60"))
MAX_SELL_TAX        = float(os.getenv("MAX_SELL_TAX", "0.10"))
MAX_CREATOR_HOLD    = float(os.getenv("MAX_CREATOR_HOLD", "0.20"))
MIN_LIQ_SOL         = float(os.getenv("MIN_LIQ_SOL", "2"))
MIN_HOLDERS         = int(os.getenv("MIN_HOLDERS", "10"))

# Порог для фоллбека Dexscreener (ликвидность в USD)
MIN_LIQ_USD         = float(os.getenv("MIN_LIQ_USD", "5000"))

# Тестовый режим: только отчёты, без сделок
TEST_MODE           = os.getenv("TEST_MODE", "1") == "1"

# Диагностика и повторные попытки при пустых данных
DEBUG_API           = os.getenv("DEBUG_API", "1") == "1"
RETRY_DELAY_SEC     = float(os.getenv("RETRY_DELAY_SEC", "3"))
MAX_META_ATTEMPTS   = int(os.getenv("MAX_META_ATTEMPTS", "2"))

WS_URL  = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

JUP_BASE  = "https://quote-api.jup.ag/v6"
WSOL_MINT = "So11111111111111111111111111111111111111112"

assert HELIUS_API_KEY, "HELIUS_API_KEY обязателен"
assert PUMPFUN_PROGRAM_ID, "PUMPFUN_PROGRAM_ID обязателен"
assert USER_PUBKEY, "USER_PUBKEY обязателен (для simulate Jupiter)"


# ========= ХЕЛПЕРЫ ФОРМАТИРОВАНИЯ =========
def _ok(v: bool) -> str:
    return "✅" if v else "❌"

def _na() -> str:
    return "ℹ️"

def _short(addr: str) -> str:
    return f"{addr[:4]}…{addr[-4:]}" if addr and len(addr) > 10 else (addr or "")

def _dbg(label: str, payload):
    if DEBUG_API:
        try:
            print(f"[DBG] {label}: {payload}")
        except Exception:
            print(f"[DBG] {label}: <не удалось распечатать>")


# ========= HTTP (httpx + ретраи) =========
async def _http_json(url: str, method: str = "GET", payload=None, timeout: float = 8.0, attempts: int = 4, headers=None):
    last_err = None
    for i in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
                if method == "GET":
                    r = await client.get(url)
                else:
                    r = await client.post(url, json=payload)
                if r.status_code == 200:
                    return r.json()
                last_err = f"http {r.status_code}"
        except Exception as e:
            last_err = str(e)
        await asyncio.sleep(min(0.5 * (2 ** i), 5) + random.uniform(0, 0.3))
    print(f"[HTTP] ошибка {method} {url}: {last_err}")
    return None


# ========= Helius / Jupiter =========
async def helius_get_tx(signature: str) -> dict:
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
        "params": [signature, {"encoding": "jsonParsed", "commitment": "confirmed"}]
    }
    return await _http_json(RPC_URL, method="POST", payload=payload)

async def get_block_time(signature: str) -> Optional[float]:
    j = await helius_get_tx(signature)
    bt = (j.get("result") or {}).get("blockTime") if j else None
    return float(bt) if bt is not None else None

async def get_account_info_jsonparsed(pubkey: str) -> dict:
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
        "params": [pubkey, {"encoding": "jsonParsed", "commitment": "confirmed"}]
    }
    j = await _http_json(RPC_URL, method="POST", payload=payload)
    return (j.get("result") or {}).get("value", {}) or {}

async def get_token_metadata(mint: str) -> dict:
    url = f"https://api.helius.xyz/v0/tokens/metadata?api-key={HELIUS_API_KEY}&mints[]={mint}"
    j = await _http_json(url)
    if not j:
        _dbg("meta:http_empty", j)
        return {}
    arr = (j or {}).get("tokens") or []
    if not arr:
        _dbg("meta:no_tokens", j)
    return arr[0] if arr else {}

async def get_token_holders_count(mint: str) -> Optional[int]:
    url = f"https://api.helius.xyz/v0/tokens/holders?api-key={HELIUS_API_KEY}&mint={mint}&page=1&limit=1"
    j = await _http_json(url)
    if not j:
        _dbg("holders:http_empty", j)
        return None
    if isinstance(j, dict) and "total" in j:
        return int(j["total"])
    if isinstance(j, list):
        _dbg("holders:list_no_total", j[:3])
        return None
    _dbg("holders:unknown_shape", j)
    return None

def extract_mints_from_tx_json(tx_json: dict) -> List[str]:
    res: List[str] = []
    tx = tx_json.get("result") if tx_json else None
    if not tx:
        return res

    meta = tx.get("meta") or {}
    for group in (meta.get("innerInstructions") or []):
        for ix in group.get("instructions", []):
            parsed = ix.get("parsed") or {}
            if isinstance(parsed, dict) and parsed.get("type") in ("initializeMint", "initializeMint2", "mintTo"):
                mint = (parsed.get("info") or {}).get("mint")
                if mint:
                    res.append(mint)

    msg = tx.get("transaction", {}).get("message", {}) or {}
    for ix in (msg.get("instructions") or []):
        parsed = ix.get("parsed") or {}
        if isinstance(parsed, dict) and parsed.get("type") in ("initializeMint", "initializeMint2", "mintTo"):
            mint = (parsed.get("info") or {}).get("mint")
            if mint:
                res.append(mint)

    return list(dict.fromkeys(res))


# ========= Honeypot / Котировки =========
def _mint_risk_flags(parsed_acc: dict) -> list:
    risks = []
    info = (parsed_acc.get("data") or {}).get("parsed", {}).get("info", {}) or {}
    if info.get("mintAuthority"):
        risks.append("mintAuthority не отозван")
    if info.get("freezeAuthority"):
        risks.append("freezeAuthority установлен")
    ext = info.get("extensions") or {}
    if ext:
        if "transferHook" in ext:
            risks.append("Token-2022 transferHook")
        tf = ext.get("transferFeeConfig") or {}
        bps = tf.get("transferFeeBasisPoints")
        if isinstance(bps, int) and bps > 1000:
            risks.append(f"комиссия за перевод {bps/100:.2f}%")
    return risks

async def jup_quote(mint_in: str, amount_in: int) -> Optional[dict]:
    url = (
        f"{JUP_BASE}/quote"
        f"?inputMint={mint_in}"
        f"&outputMint={WSOL_MINT}"
        f"&amount={amount_in}"
        f"&slippageBps=100"
        f"&swapMode=ExactIn"
    )
    q = await _http_json(url, timeout=8.0, attempts=4)
    if not q:
        return None
    if isinstance(q, dict) and (q.get("outAmount") or (q.get("routes") or [])):
        return q
    return None

async def jup_swap_instructions(quote: dict) -> Optional[dict]:
    if not USER_PUBKEY:
        return None
    url = f"{JUP_BASE}/swap-instructions"
    payload = {
        "quoteResponse": quote,
        "userPublicKey": USER_PUBKEY,
        "wrapAndUnwrapSol": True,
        "useSharedAccounts": True,
        "asLegacyTransaction": False
    }
    return await _http_json(url, method="POST", payload=payload)

async def helius_simulate(ixs_resp: dict) -> Tuple[bool, str]:
    msg_b64 = ixs_resp.get("swapTransactionMessage") if ixs_resp else None
    if not msg_b64:
        return (False, "продажа недоступна (нет swap-инструкций)")
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "simulateTransaction",
        "params": [
            msg_b64,
            {"encoding": "base64", "sigVerify": False, "replaceRecentBlockhash": True, "commitment": "processed"}
        ]
    }
    j = await _http_json(RPC_URL, method="POST", payload=payload)
    err = (j.get("result") or {}).get("err") if j else "нет результата"
    ok = err is None
    reason = "ок" if ok else f"ошибка симуляции: {err}"
    return (ok, reason)

async def honeypot_check(mint: str) -> Tuple[bool, str]:
    parsed = await get_account_info_jsonparsed(mint)
    risks = _mint_risk_flags(parsed)
    if risks:
        return (False, " ; ".join(risks))

    info = (parsed.get("data") or {}).get("parsed", {}).get("info", {}) or {}
    try:
        supply = int(info.get("supply", "0"))
        dec = int(info.get("decimals", 9))
    except Exception:
        supply, dec = 0, 9

    test_amount = max(supply // 10_000, 10 ** max(dec - 6, 0))
    if test_amount == 0:
        test_amount = 10 ** max(dec - 6, 0)

    quote = await jup_quote(mint, test_amount)
    if not quote:
        return (False, "нет маршрута в Jupiter (нет пула/ликвидности)")
    ixs = await jup_swap_instructions(quote)
    if not ixs:
        return (False, "продажа недоступна (нет swap-инструкций)")
    ok, reason = await helius_simulate(ixs)
    return (ok, reason)

async def jup_price_spl_in_sol(mint: str, amount_in_atoms: Optional[int] = None) -> Optional[float]:
    parsed = await get_account_info_jsonparsed(mint)
    info = (parsed.get("data") or {}).get("parsed", {}).get("info", {}) or {}
    dec = int(info.get("decimals", 9))
    if amount_in_atoms is None:
        amount_in_atoms = 10 ** dec

    q = await jup_quote(mint, amount_in_atoms)
    if not q:
        return None

    out_amount = None
    if "outAmount" in q:
        out_amount = int(q["outAmount"])
    elif "routes" in q and q["routes"]:
        out_amount = int(q["routes"][0]["outAmount"])

    if not out_amount:
        return None

    sol_for_amount = out_amount / 1_000_000_000
    price_sol_per_token = sol_for_amount / amount_in_atoms
    return price_sol_per_token


# ========= Dexscreener fallback (без ключей) =========
async def dexs_pairs_for_token(mint: str) -> dict | None:
    """
    Возвращает информацию по парам токена из DexScreener.
    Нужен для того, чтобы понять: есть ли пул и оценить ликвидность (USD).
    """
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                _dbg("dexs:http", f"status {r.status_code}")
                return None
            data = r.json() or {}
    except Exception as e:
        _dbg("dexs:exc", str(e))
        return None

    pairs = (data.get("pairs") or [])
    if not pairs:
        return None

    best = max(pairs, key=lambda p: (p.get("liquidity", {}).get("usd") or 0))
    liq_usd = (best.get("liquidity") or {}).get("usd")
    return {"has_pool": True, "liquidity_usd": float(liq_usd) if isinstance(liq_usd, (int, float)) else None}


# ========= ОЦЕНКА ТОКЕНА =========
async def evaluate_token(mint: str, signature: Optional[str]):
    """
    Возвращает: passed_all(bool), metrics(dict), meta(dict)
    С ретраями, причинами 'н/д' и фоллбеком Dexscreener по ликвидности.
    """
    metrics = {
        "age_s": None, "age_ok": False,
        "honeypot_ok": False, "honeypot_reason": "",
        "sell_tax": None, "sell_tax_ok": True,
        "lp_locked": None, "lp_locked_ok": True,
        "creator_hold": None, "creator_hold_ok": True,
        "holders": None, "holders_ok": True, "holders_reason": "",
        "liquidity": None, "liquidity_ok": True, "liquidity_reason": "",
        "marketcap": None,
        "sellable": None,
        "price_sol": None,
    }

    # Возраст
    now = time.time()
    created_sec = None
    if signature:
        bt = await get_block_time(signature)
        if bt:
            created_sec = bt
    if created_sec is not None:
        age = now - created_sec
        metrics["age_s"] = age
        metrics["age_ok"] = age <= MAX_TOKEN_AGE_SEC

    # Honeypot / Продаваемость
    hp_ok, hp_reason = await honeypot_check(mint)
    metrics["honeypot_ok"] = hp_ok
    metrics["honeypot_reason"] = "OK" if hp_ok else hp_reason
    metrics["sellable"] = hp_ok

    # Метаданные/холдеры — умные ретраи
    meta = {}
    holders_count = None
    for attempt in range(1, MAX_META_ATTEMPTS + 1):
        meta = await get_token_metadata(mint) or {}
        holders_count = await get_token_holders_count(mint)
        has_any_meta = any(k in meta for k in ("liquidity","sellTax","creatorHold","lpLocked","marketCap","marketCapUsd"))
        if has_any_meta or holders_count is not None:
            break
        _dbg("meta_retry", {"attempt": attempt, "reason": "пустые метаданные/холдеры"})
        await asyncio.sleep(RETRY_DELAY_SEC)

    # причины н/д
    if ("liquidity" not in meta) or (meta.get("liquidity") is None):
        metrics["liquidity_reason"] = "нет пула/ликвидности (Helius 404/пусто)"
    if holders_count is None:
        metrics["holders_reason"] = "ещё нет записей (Helius 404/пусто)"

    # Liquidity из Helius (если есть)
    liq = meta.get("liquidity")
    if isinstance(liq, (int, float)):
        metrics["liquidity"] = float(liq)
        metrics["liquidity_ok"] = float(liq) >= MIN_LIQ_SOL
        metrics["liquidity_reason"] = ""

    # --- Фоллбек на Dexscreener по ликвидности ---
    if metrics["liquidity"] is None:
        ds = await dexs_pairs_for_token(mint)
        if ds and ds.get("has_pool"):
            liq_usd = ds.get("liquidity_usd")
            if isinstance(liq_usd, (int, float)):
                metrics["liquidity"] = liq_usd  # в USD
                metrics["liquidity_ok"] = liq_usd >= MIN_LIQ_USD
                metrics["liquidity_reason"] = "по данным Dexscreener (USD)"
            else:
                metrics["liquidity"] = 0.0
                metrics["liquidity_ok"] = True
                metrics["liquidity_reason"] = "есть пул (Dexscreener)"

    # Остальные метрики из meta
    sell_tax = meta.get("sellTax")
    if isinstance(sell_tax, (int, float)):
        metrics["sell_tax"] = float(sell_tax)
        metrics["sell_tax_ok"] = float(sell_tax) <= MAX_SELL_TAX

    lp_locked = meta.get("lpLocked")
    if lp_locked is not None:
        metrics["lp_locked"] = bool(lp_locked)
        metrics["lp_locked_ok"] = bool(lp_locked)

    creator_hold = meta.get("creatorHold")
    if isinstance(creator_hold, (int, float)):
        metrics["creator_hold"] = float(creator_hold)
        metrics["creator_hold_ok"] = float(creator_hold) <= MAX_CREATOR_HOLD

    if holders_count is not None:
        metrics["holders"] = int(holders_count)
        metrics["holders_ok"] = metrics["holders"] >= MIN_HOLDERS
        metrics["holders_reason"] = ""

    mc = meta.get("marketCap") or meta.get("marketCapUsd")
    if isinstance(mc, (int, float)):
        metrics["marketcap"] = float(mc)

    # Цена (инфо)
    entry_price = await jup_price_spl_in_sol(mint)
    metrics["price_sol"] = entry_price

    # Итоговый вердикт
    hard_ok = (metrics["age_ok"] is True) and (metrics["honeypot_ok"] is True)
    soft_checks = []
    for key_ok in ("sell_tax_ok", "lp_locked_ok", "creator_hold_ok", "holders_ok", "liquidity_ok"):
        available = metrics.get(key_ok.replace("_ok","")) is not None
        if available:
            soft_checks.append(bool(metrics.get(key_ok)))
    soft_ok = all(soft_checks) if soft_checks else True

    passed_all = bool(hard_ok and soft_ok)
    return passed_all, metrics, meta


# ========= ОСНОВНОЙ ЦИКЛ (WS + отчёты) =========
async def listen_pumpfun():
    async def on_open(ws):
        sub = {
            "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
            "params": [{"mentions": [PUMPFUN_PROGRAM_ID]}, {"commitment": "finalized"}]
        }
        await ws.send(json.dumps(sub))
        print("🛰 Подписка на Pump.fun логи через Helius оформлена")

    async def keepalive(ws, ping_interval=20, ping_timeout=15):
        while True:
            await asyncio.sleep(ping_interval * 0.9)
            try:
                pong_waiter = await ws.ping()
                await asyncio.wait_for(pong_waiter, timeout=ping_timeout)
            except Exception:
                try:
                    await ws.close(code=1011, reason="keepalive failure")
                except Exception:
                    pass
                return

    backoff = 1
    while True:
        try:
            async with websockets.connect(
                WS_URL,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
                max_queue=1000
            ) as ws:
                await on_open(ws)
                backoff = 1

                ka = asyncio.create_task(keepalive(ws))

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue

                    if msg.get("method") != "logsNotification":
                        continue
                    value = msg.get("params", {}).get("result", {}).get("value", {})
                    signature = value.get("signature")
                    if not signature:
                        continue

                    tx_json = await helius_get_tx(signature)
                    if not tx_json:
                        continue
                    mints = extract_mints_from_tx_json(tx_json)
                    if not mints:
                        continue

                    for mint in mints:
                        try:
                            passed, m, meta = await evaluate_token(mint, signature)
                            sym  = meta.get("symbol") or meta.get("tokenSymbol") or "UNK"
                            name = meta.get("name") or "Unnamed"

                            age_str  = f"{int(m['age_s'])}с" if m["age_s"] is not None else "н/д"
                            # вывод ликвидности: SOL (если Helius) или USD (если Dexscreener)
                            if m["liquidity"] is not None and m.get("liquidity_reason","").endswith("(USD)"):
                                liq_val = f"{m['liquidity']:.0f} USD"
                            elif m["liquidity"] is not None:
                                liq_val = f"{m['liquidity']:.0f} SOL"
                            else:
                                liq_val = f"н/д{(' — ' + m['liquidity_reason']) if m.get('liquidity_reason') else ''}"

                            hold_str = (
                                str(m["holders"])
                                if m["holders"] is not None
                                else f"н/д{(' — ' + m['holders_reason']) if m.get('holders_reason') else ''}"
                            )
                            st_str   = f"{m['sell_tax']:.2f}" if m["sell_tax"] is not None else "н/д"
                            ch_str   = f"{m['creator_hold']:.2f}" if m["creator_hold"] is not None else "н/д"
                            lp_str   = "ДА" if m["lp_locked"] else ("НЕТ" if m["lp_locked"] is not None else "н/д")
                            sellable_str = "ДА" if m["sellable"] else "НЕТ"
                            mc_str   = f"${m['marketcap']:,.0f}" if m["marketcap"] is not None else "н/д"

                            report = (
                                f"<code>ТОКЕН:</code> <b>{name}</b> ({sym}) | <code>{_short(mint)}</code>\n"
                                f"<code>Возраст:</code> {age_str} {_ok(m['age_ok'])}\n"
                                f"<code>Продажа (honeypot):</code> {m['honeypot_reason']} {_ok(m['honeypot_ok'])}\n"
                                f"<code>Ликвидность:</code> {liq_val} "
                                    f"{_ok(m['liquidity_ok']) if m['liquidity'] is not None else _na()}\n"
                                f"<code>Рын. кап.:</code> {mc_str} {_na()}\n"
                                f"<code>Холдеров:</code> {hold_str} "
                                    f"{_ok(m['holders_ok']) if m['holders'] is not None else _na()}\n"
                                f"<code>Налог продажи:</code> {st_str} "
                                    f"{_ok(m['sell_tax_ok']) if m['sell_tax'] is not None else _na()}\n"
                                f"<code>Доля создателя:</code> {ch_str} "
                                  f"{_ok(m['creator_hold_ok']) if m['creator_hold'] is not None else _na()}\n"
                                f"<code>LP заблокирована:</code> {lp_str} "
                                    f"{_ok(m['lp_locked_ok']) if m['lp_locked'] is not None else _na()}\n"
                                f"<code>Продаваемость:</code> {sellable_str} {_ok(m['sellable'])}\n"
                                f"<code>---</code>\n"
                                f"{'✅' if passed else '⚠️'} <b>Рекомендация:</b> {'BUY' if passed else 'RISK'}"
                            )

                            print(report)
                            send_message(report)

                            if passed and not TEST_MODE:
                                entry_price = m["price_sol"] or 0.0
                                deal.buy({"mint": mint, "symbol": sym}, entry_price, report)

                        except Exception as e:
                            print(f"[handler] ошибка для {mint}: {e}")

                ka.cancel()

        except websockets.ConnectionClosedError as e:
            print(f"⚠ WS закрыт: {e.code} {e.reason}")
        except Exception as e:
            print(f"⚠ WS ошибка: {e}")

        sleep_s = min(60, backoff) + random.uniform(0, 0.5 * backoff)
        print(f"↪ переподключение через {sleep_s:.1f}с…")
        await asyncio.sleep(sleep_s)
        backoff = min(60, backoff * 2)  
