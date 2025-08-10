import os
import time
import json
import asyncio
import random
from typing import Optional, Tuple, List, Dict, Any

import websockets
import aiohttp

from telegram import send_message
import deal


# ========= КОНФИГ =========
HELIUS_API_KEY      = os.getenv("HELIUS_API_KEY")
PUMPFUN_PROGRAM_ID  = os.getenv("PUMPFUN_PROGRAM_ID")
USER_PUBKEY         = os.getenv("USER_PUBKEY")

assert HELIUS_API_KEY, "HELIUS_API_KEY обязателен"
assert PUMPFUN_PROGRAM_ID, "PUMPFUN_PROGRAM_ID обязателен"
assert USER_PUBKEY, "USER_PUBKEY обязателен"

# Порог/фильтры
MAX_TOKEN_AGE_SEC   = int(os.getenv("MAX_TOKEN_AGE_SEC", "60"))
MAX_SELL_TAX        = float(os.getenv("MAX_SELL_TAX", "0.10"))
MAX_CREATOR_HOLD    = float(os.getenv("MAX_CREATOR_HOLD", "0.20"))
MIN_LIQ_SOL         = float(os.getenv("MIN_LIQ_SOL", "2"))
MIN_LIQ_USD         = float(os.getenv("MIN_LIQ_USD", "5000"))
MIN_HOLDERS         = int(os.getenv("MIN_HOLDERS", "10"))

# Поведение
TEST_MODE           = os.getenv("TEST_MODE", "1") == "1"
DEBUG_API           = os.getenv("DEBUG_API", "1") == "1"
RETRY_DELAYS        = [30, 60, 120]  # сек для повторных проверок
MAX_TOKENS_PER_RUN  = int(os.getenv("MAX_TOKENS_PER_RUN", "10"))

# Сети/эндпоинты
WS_URL  = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
JUP_BASE  = "https://quote-api.jup.ag/v6"
WSOL_MINT = "So11111111111111111111111111111111111111112"


# ========= УТИЛИТЫ =========
def _ok(v: bool) -> str:
    return "✅" if v else "❌"

def _na() -> str:
    return "ℹ️"

def _short(addr: str) -> str:
    return f"{addr[:4]}…{addr[-4:]}" if addr and len(addr) > 10 else (addr or "")

def _dbg(label: str, payload: Any):
    if DEBUG_API:
        try:
            print(f"[DBG] {label}: {payload}")
        except Exception:
            print(f"[DBG] {label}: <не печатается>")

def _label_map() -> Dict[str, str]:
    return {
        "age": "Возраст",
        "honeypot": "Продажа (honeypot)",
        "liquidity": "Ликвидность",
        "marketcap": "Рын. кап.",
        "holders": "Холдеров",
        "sell_tax": "Налог продажи",
        "creator_hold": "Доля создателя",
        "lp_locked": "LP заблокирована",
        "sellable": "Продаваемость",
        "price_sol": "Цена (SOL)"
    }


# ========= HTTP с ретраями =========
async def fetch_with_retry(session: aiohttp.ClientSession, url: str, *, method: str = "GET",
                           payload: Any = None, headers: Dict[str, str] = None,
                           max_attempts: int = 3, delay: float = 2.0, timeout: float = 12.0) -> Optional[Dict]:
    for attempt in range(1, max_attempts + 1):
        try:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        print(f"[RETRY] {attempt}/{max_attempts} status {resp.status} for {url}")
            else:
                async with session.post(url, json=payload, headers=headers, timeout=timeout) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        print(f"[RETRY] {attempt}/{max_attempts} status {resp.status} for {url}")
        except Exception as e:
            print(f"[RETRY] {attempt}/{max_attempts} error {e} for {url}")
        if attempt < max_attempts:
            await asyncio.sleep(delay)
    return None


# ========= Helius / Jupiter helpers =========
async def helius_get_tx(session: aiohttp.ClientSession, signature: str) -> dict:
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
        "params": [signature, {"encoding": "jsonParsed", "commitment": "confirmed"}]
    }
    return await fetch_with_retry(session, RPC_URL, method="POST", payload=payload)

async def get_block_time(session: aiohttp.ClientSession, signature: str) -> Optional[float]:
    j = await helius_get_tx(session, signature)
    bt = (j.get("result") or {}).get("blockTime") if j else None
    return float(bt) if bt is not None else None

async def get_account_info_jsonparsed(session: aiohttp.ClientSession, pubkey: str) -> dict:
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
        "params": [pubkey, {"encoding": "jsonParsed", "commitment": "confirmed"}]
    }
    j = await fetch_with_retry(session, RPC_URL, method="POST", payload=payload)
    return (j.get("result") or {}).get("value", {}) or {}

async def get_token_metadata(session: aiohttp.ClientSession, mint: str) -> dict:
    url = f"https://api.helius.xyz/v0/tokens/metadata?api-key={HELIUS_API_KEY}&mints[]={mint}"
    j = await fetch_with_retry(session, url)
    arr = (j or {}).get("tokens") or []
    if not arr:
        _dbg("meta:no_tokens", j)
    return arr[0] if arr else {}

async def get_token_holders_count(session: aiohttp.ClientSession, mint: str) -> Optional[int]:
    url = f"https://api.helius.xyz/v0/tokens/holders?api-key={HELIUS_API_KEY}&mint={mint}&page=1&limit=1"
    j = await fetch_with_retry(session, url)
    if not j:
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


# ========= Honeypot / Quotes =========
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

async def jup_quote(session: aiohttp.ClientSession, mint_in: str, amount_in: int) -> Optional[dict]:
    url = (
        f"{JUP_BASE}/quote"
        f"?inputMint={mint_in}"
        f"&outputMint={WSOL_MINT}"
        f"&amount={amount_in}"
        f"&slippageBps=100"
        f"&swapMode=ExactIn"
    )
    return await fetch_with_retry(session, url)

async def jup_swap_instructions(session: aiohttp.ClientSession, quote: dict) -> Optional[dict]:
    url = f"{JUP_BASE}/swap-instructions"
    payload = {
        "quoteResponse": quote,
        "userPublicKey": USER_PUBKEY,
        "wrapAndUnwrapSol": True,
        "useSharedAccounts": True,
        "asLegacyTransaction": False
    }
    return await fetch_with_retry(session, url, method="POST", payload=payload)

async def helius_simulate(session: aiohttp.ClientSession, ixs_resp: dict) -> Tuple[bool, str]:
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
    j = await fetch_with_retry(session, RPC_URL, method="POST", payload=payload)
    err = (j.get("result") or {}).get("err") if j else "нет результата"
    ok = err is None
    reason = "OK" if ok else f"ошибка симуляции: {err}"
    return (ok, reason)

async def honeypot_check(session: aiohttp.ClientSession, mint: str) -> Tuple[bool, str]:
    parsed = await get_account_info_jsonparsed(session, mint)
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

    quote = await jup_quote(session, mint, test_amount)
    if not quote:
        return (False, "нет маршрута в Jupiter (нет пула/ликвидности)")
    ixs = await jup_swap_instructions(session, quote)
    if not ixs:
        return (False, "продажа недоступна (нет swap-инструкций)")
    ok, reason = await helius_simulate(session, ixs)
    return (ok, reason)

async def jup_price_spl_in_sol(session: aiohttp.ClientSession, mint: str, amount_in_atoms: Optional[int] = None) -> Optional[float]:
    parsed = await get_account_info_jsonparsed(session, mint)
    info = (parsed.get("data") or {}).get("parsed", {}).get("info", {}) or {}
    dec = int(info.get("decimals", 9))
    if amount_in_atoms is None:
        amount_in_atoms = 10 ** dec

    q = await jup_quote(session, mint, amount_in_atoms)
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


# ========= Dexscreener fallback =========
async def dexs_pairs_for_token(session: aiohttp.ClientSession, mint: str) -> dict | None:
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
    j = await fetch_with_retry(session, url)
    if not j:
        return None
    pairs = (j.get("pairs") or [])
    if not pairs:
        return None
    best = max(pairs, key=lambda p: (p.get("liquidity", {}).get("usd") or 0))
    liq_usd = (best.get("liquidity") or {}).get("usd")
    return {"has_pool": True, "liquidity_usd": float(liq_usd) if isinstance(liq_usd, (int, float)) else None}


# ========= ОЦЕНКА ТОКЕНА =========
async def evaluate_token(session: aiohttp.ClientSession, mint: str, signature: Optional[str]) -> tuple[bool, dict, dict]:
    """
    Возвращает: (passed_all, metrics, meta)
    metrics поля:
      age_s, age_ok
      honeypot_ok, honeypot_reason
      sell_tax, sell_tax_ok
      lp_locked, lp_locked_ok
      creator_hold, creator_hold_ok
      holders, holders_ok
      liquidity, liquidity_ok, liquidity_src ('SOL'|'USD'|'')
      marketcap
      sellable
      price_sol
    Отсутствующее значение помечаем '⏳'.
    """
    m = {
        "age_s": "⏳", "age_ok": False,
        "honeypot_ok": False, "honeypot_reason": "⏳",
        "sell_tax": "⏳", "sell_tax_ok": True,
        "lp_locked": "⏳", "lp_locked_ok": True,
        "creator_hold": "⏳", "creator_hold_ok": True,
        "holders": "⏳", "holders_ok": True,
        "liquidity": "⏳", "liquidity_ok": True, "liquidity_src": "",
        "marketcap": "⏳",
        "sellable": False,
        "price_sol": "⏳",
    }

    meta: Dict[str, Any] = {}

    # Age
    if signature:
        bt = await get_block_time(session, signature)
        if bt:
            age = time.time() - bt
            m["age_s"] = age
            m["age_ok"] = age <= MAX_TOKEN_AGE_SEC

    # Honeypot / Sellable
    hp_ok, hp_reason = await honeypot_check(session, mint)
    m["honeypot_ok"] = hp_ok
    m["honeypot_reason"] = "OK" if hp_ok else hp_reason
    m["sellable"] = hp_ok

    # Metadata + holders
    meta = await get_token_metadata(session, mint) or {}
    holders_count = await get_token_holders_count(session, mint)

    # soft fields
    sell_tax = meta.get("sellTax")
    if isinstance(sell_tax, (int, float)):
        m["sell_tax"] = float(sell_tax)
        m["sell_tax_ok"] = float(sell_tax) <= MAX_SELL_TAX

    lp_locked = meta.get("lpLocked")
    if lp_locked is not None:
        m["lp_locked"] = bool(lp_locked)
        m["lp_locked_ok"] = bool(lp_locked)

    creator_hold = meta.get("creatorHold")
    if isinstance(creator_hold, (int, float)):
        m["creator_hold"] = float(creator_hold)
        m["creator_hold_ok"] = float(creator_hold) <= MAX_CREATOR_HOLD

    if holders_count is not None:
        m["holders"] = int(holders_count)
        m["holders_ok"] = int(holders_count) >= MIN_HOLDERS

    liq = meta.get("liquidity")
    if isinstance(liq, (int, float)):
        m["liquidity"] = float(liq)
        m["liquidity_ok"] = float(liq) >= MIN_LIQ_SOL
        m["liquidity_src"] = "SOL"

    mc = meta.get("marketCap") or meta.get("marketCapUsd")
    if isinstance(mc, (int, float)):
        m["marketcap"] = float(mc)

    # Liquidity fallback Dexscreener (если Helius пуст)
    if m["liquidity"] == "⏳":
        ds = await dexs_pairs_for_token(session, mint)
        if ds and ds.get("has_pool"):
            liq_usd = ds.get("liquidity_usd")
            if isinstance(liq_usd, (int, float)):
                m["liquidity"] = float(liq_usd)
                m["liquidity_ok"] = float(liq_usd) >= MIN_LIQ_USD
                m["liquidity_src"] = "USD"

    # Live price (инфо)
    price_sol = await jup_price_spl_in_sol(session, mint)
    if isinstance(price_sol, (int, float, float)):
        m["price_sol"] = float(price_sol)

    # Verdict
    hard_ok = (m["age_ok"] is True) and (m["honeypot_ok"] is True)

    soft_checks = []
    for key_ok, base_key in [
        ("sell_tax_ok", "sell_tax"),
        ("lp_locked_ok", "lp_locked"),
        ("creator_hold_ok", "creator_hold"),
        ("holders_ok", "holders"),
        ("liquidity_ok", "liquidity"),
    ]:
        available = m.get(base_key) != "⏳"
        if available:
            soft_checks.append(bool(m.get(key_ok)))
    soft_ok = all(soft_checks) if soft_checks else True

    passed_all = bool(hard_ok and soft_ok)
    return passed_all, m, meta


# ========= ФОРМАТИРОВАНИЕ СООБЩЕНИЙ =========
def _fmt_value_and_icon(key: str, m: dict) -> tuple[str, str]:
    # Возвращает (строка значения, иконка статуса/ℹ️)
    if m.get(key) == "⏳":
        return "⏳", _na()
    if key == "age_s":
        return (f"{int(m['age_s'])}с", _ok(m["age_ok"]))
    if key == "honeypot":
        return (m["honeypot_reason"], _ok(m["honeypot_ok"]))
    if key == "liquidity":
        if m["liquidity"] == "⏳":
            return "⏳", _na()
        if m.get("liquidity_src") == "USD":
            return f"{m['liquidity']:.0f} USD", _ok(m["liquidity_ok"])
        else:
            return f"{m['liquidity']:.0f} SOL", _ok(m["liquidity_ok"])
    if key == "holders":
        return (str(m["holders"]), _ok(m["holders_ok"]))
    if key == "sell_tax":
        return (f"{m['sell_tax']:.2f}", _ok(m["sell_tax_ok"]))
    if key == "creator_hold":
        return (f"{m['creator_hold']:.2f}", _ok(m["creator_hold_ok"]))
    if key == "lp_locked":
        if m["lp_locked"] == "⏳":
            return "⏳", _na()
        return ("ДА" if m["lp_locked"] else "НЕТ", _ok(m["lp_locked_ok"]))
    if key == "sellable":
        return ("ДА" if m["sellable"] else "НЕТ", _ok(m["sellable"]))
    if key == "marketcap":
        if m["marketcap"] == "⏳":
            return "⏳", _na()
        return (f"${m['marketcap']:,.0f}", _na())
    if key == "price_sol":
        if m["price_sol"] == "⏳":
            return "⏳", _na()
        return (f"{m['price_sol']:.10f} SOL", _na())
    return (str(m.get(key)), _na())

def build_full_report(name: str, symbol: str, mint: str, m: dict, passed: bool) -> str:
    age_str, age_ic = _fmt_value_and_icon("age_s", m)
    hp_str, hp_ic   = _fmt_value_and_icon("honeypot", {"honeypot_reason": m["honeypot_reason"], "honeypot_ok": m["honeypot_ok"]})
    liq_str, liq_ic = _fmt_value_and_icon("liquidity", m)
    mc_str, mc_ic   = _fmt_value_and_icon("marketcap", m)
    hold_str, hold_ic = _fmt_value_and_icon("holders", m)
    st_str, st_ic   = _fmt_value_and_icon("sell_tax", m)
    ch_str, ch_ic   = _fmt_value_and_icon("creator_hold", m)
    lp_str, lp_ic   = _fmt_value_and_icon("lp_locked", m)
    sellable_str, sellable_ic = _fmt_value_and_icon("sellable", m)

    report = (
        f"<code>ТОКЕН:</code> <b>{name}</b> ({symbol}) | <code>{_short(mint)}</code>\n"
        f"<code>Возраст:</code> {age_str} {age_ic}\n"
        f"<code>Продажа (honeypot):</code> {hp_str} {hp_ic}\n"
        f"<code>Ликвидность:</code> {liq_str} {liq_ic}\n"
        f"<code>Рын. кап.:</code> {mc_str} {mc_ic}\n"
        f"<code>Холдеров:</code> {hold_str} {hold_ic}\n"
        f"<code>Налог продажи:</code> {st_str} {st_ic}\n"
        f"<code>Доля создателя:</code> {ch_str} {ch_ic}\n"
        f"<code>LP заблокирована:</code> {lp_str} {lp_ic}\n"
        f"<code>Продаваемость:</code> {sellable_str} {sellable_ic}\n"
        f"<code>---</code>\n"
        f"{'✅' if passed else '⚠️'} <b>Рекомендация:</b> {'BUY' if passed else 'RISK'}"
    )
    return report

def build_short_update(symbol: str, updated_display: Dict[str, str]) -> str:
    lines = [f"🔄 Обновлено для {symbol}:"]
    for k, v in updated_display.items():
        lines.append(f"• {k}: {v}")
    return "\n".join(lines)


# ========= ПОВТОРНЫЕ ПРОВЕРКИ =========
_pending: Dict[str, Dict[str, Any]] = {}  # mint -> {missing:set(str), attempt:int, symbol:str, name:str}

async def retry_check_task(session: aiohttp.ClientSession, mint: str):
    data = _pending.get(mint)
    if not data:
        return
    missing: set = data["missing"]
    symbol: str = data["symbol"]
    name: str = data["name"]
    attempt: int = data.get("attempt", 0)

    for i, delay in enumerate(RETRY_DELAYS, start=1):
        if not missing:
            break
        await asyncio.sleep(delay)
        print(f"[RETRY-CHECK] {i}/{len(RETRY_DELAYS)} for {symbol} ({_short(mint)}), waiting for: {', '.join(sorted(missing))}")

        # Переоценка токена целиком (проще и стабильнее), но сравниваем ТОЛЬКО недостающее
        _, m_new, _ = await evaluate_token(session, mint, None)

        updated_display: Dict[str, str] = {}
        # Сопоставление ключей -> как их красиво показать
        for key in list(missing):
            # Вычислим строчку отображения для краткого апдейта
            if key == "age_s":
                if m_new["age_s"] != "⏳":
                    updated_display["Возраст"] = f"{int(m_new['age_s'])}с"
                    missing.discard("age_s")
            elif key == "honeypot":
                if m_new["honeypot_ok"] != "⏳":
                    updated_display["Продажа (honeypot)"] = m_new["honeypot_reason"]
                    missing.discard("honeypot")
            elif key == "liquidity":
                if m_new["liquidity"] != "⏳":
                    if m_new.get("liquidity_src") == "USD":
                        updated_display["Ликвидность"] = f"{m_new['liquidity']:.0f} USD"
                    else:
                        updated_display["Ликвидность"] = f"{m_new['liquidity']:.0f} SOL"
                    missing.discard("liquidity")
            elif key == "marketcap":
                if m_new["marketcap"] != "⏳":
                    updated_display["Рын. кап."] = f"${m_new['marketcap']:,.0f}"
                    missing.discard("marketcap")
            elif key == "holders":
                if m_new["holders"] != "⏳":
                    updated_display["Холдеров"] = str(m_new["holders"])
                    missing.discard("holders")
            elif key == "sell_tax":
                if m_new["sell_tax"] != "⏳":
                    updated_display["Налог продажи"] = f"{m_new['sell_tax']:.2f}"
                    missing.discard("sell_tax")
            elif key == "creator_hold":
                if m_new["creator_hold"] != "⏳":
                    updated_display["Доля создателя"] = f"{m_new['creator_hold']:.2f}"
                    missing.discard("creator_hold")
            elif key == "lp_locked":
                if m_new["lp_locked"] != "⏳":
                    updated_display["LP заблокирована"] = ("ДА" if m_new["lp_locked"] else "НЕТ")
                    missing.discard("lp_locked")
            elif key == "price_sol":
                if m_new["price_sol"] != "⏳":
                    updated_display["Цена (SOL)"] = f"{m_new['price_sol']:.10f} SOL"
                    missing.discard("price_sol")

        if updated_display:
            await send_message(build_short_update(symbol, updated_display))

        print(f"[RETRY-DONE] {i}/{len(RETRY_DELAYS)} for {symbol}, remaining: {', '.join(sorted(missing)) or '—'}")

    # Завершили цикл — удаляем из очереди
    _pending.pop(mint, None)


# ========= ГЛАВНЫЙ ЦИКЛ =========
async def listen_pumpfun():
    processed = 0

    async def on_open(ws):
        sub = {
            "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
            "params": [{"mentions": [PUMPFUN_PROGRAM_ID]}, {"commitment": "finalized"}]
        }
        await ws.send(json.dumps(sub))
        print("🛰 Подписка на Pump.fun логи через Helius оформлена")

    async with aiohttp.ClientSession() as session:
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

                    async for raw in ws:
                        if processed >= MAX_TOKENS_PER_RUN:
                            # Дальше просто слушаем и игнорим, чтобы не спамить
                            continue
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

                        tx_json = await helius_get_tx(session, signature)
                        if not tx_json:
                            continue
                        mints = extract_mints_from_tx_json(tx_json)
                        if not mints:
                            continue

                        for mint in mints:
                            if processed >= MAX_TOKENS_PER_RUN:
                                break
                            try:
                                passed, metrics, meta = await evaluate_token(session, mint, signature)
                                sym  = meta.get("symbol") or meta.get("tokenSymbol") or "UNK"
                                name = meta.get("name") or "Unnamed"

                                report = build_full_report(name, sym, mint, metrics, passed)
                                print(report)
                                await send_message(report)

                                # Сделка (если не тест)
                                if passed and not TEST_MODE:
                                    entry_price = metrics["price_sol"] if isinstance(metrics["price_sol"], float) else 0.0
                                    deal.buy({"mint": mint, "symbol": sym}, entry_price, report)

                                # Собираем недостающие поля для ретраев
                                missing = set()
                                if metrics["age_s"] == "⏳": missing.add("age_s")
                                if metrics["honeypot_reason"] == "⏳": missing.add("honeypot")
                                if metrics["liquidity"] == "⏳": missing.add("liquidity")
                                if metrics["marketcap"] == "⏳": missing.add("marketcap")
                                if metrics["holders"] == "⏳": missing.add("holders")
                                if metrics["sell_tax"] == "⏳": missing.add("sell_tax")
                                if metrics["creator_hold"] == "⏳": missing.add("creator_hold")
                                if metrics["lp_locked"] == "⏳": missing.add("lp_locked")
                                if metrics["price_sol"] == "⏳": missing.add("price_sol")

                                if missing:
                                    _pending[mint] = {"missing": missing, "attempt": 0, "symbol": sym, "name": name}
                                    asyncio.create_task(retry_check_task(session, mint))

                                processed += 1

                            except Exception as e:
                                print(f"[handler] ошибка для {mint}: {e}")

            except websockets.ConnectionClosedError as e:
                print(f"⚠ WS закрыт: {e.code} {e.reason}")
            except Exception as e:
                print(f"⚠ WS ошибка: {e}")

            sleep_s = min(60, backoff) + random.uniform(0, 0.5 * backoff)
            print(f"↪ переподключение через {sleep_s:.1f}с…")
            await asyncio.sleep(sleep_s)
            backoff = min(60, backoff * 2)


if __name__ == "__main__":
    asyncio.run(listen_pumpfun())
