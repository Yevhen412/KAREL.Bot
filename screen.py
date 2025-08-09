import os
import time
import json
import base64
import asyncio
import websockets
import aiohttp
from typing import Optional, Tuple
from telegram import send_message
import deal

# ========= ENV / CONFIG =========
HELIUS_API_KEY      = os.getenv("HELIUS_API_KEY")           # ОБЯЗАТЕЛЬНО
PUMPFUN_PROGRAM_ID  = os.getenv("PUMPFUN_PROGRAM_ID")       # ОБЯЗАТЕЛЬНО (актуальный Program ID Pump.fun)
USER_PUBKEY         = os.getenv("USER_PUBKEY")              # ОБЯЗАТЕЛЬНО (паблик кошелька, для Jupiter инструкций)

MAX_TOKEN_AGE_SEC   = int(os.getenv("MAX_TOKEN_AGE_SEC", "60"))   # возраст токена, сек
MAX_SELL_TAX        = float(os.getenv("MAX_SELL_TAX", "0.10"))    # мягкий фильтр (если поле есть)
MAX_CREATOR_HOLD    = float(os.getenv("MAX_CREATOR_HOLD", "0.20"))# мягкий фильтр (если поле есть)
MIN_LIQ_SOL         = float(os.getenv("MIN_LIQ_SOL", "2"))        # мягкий фильтр (если поле есть)
MIN_HOLDERS         = int(os.getenv("MIN_HOLDERS", "10"))         # мягкий фильтр (если доступно)

WS_URL  = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

JUP_BASE  = "https://quote-api.jup.ag/v6"
WSOL_MINT = "So11111111111111111111111111111111111111112"

assert HELIUS_API_KEY, "HELIUS_API_KEY is required"
assert PUMPFUN_PROGRAM_ID, "PUMPFUN_PROGRAM_ID is required"
assert USER_PUBKEY, "USER_PUBKEY is required (для Jupiter simulate)"


# ========= HELPERS =========
async def _http_json(url: str, method: str = "GET", payload=None, timeout: int = 20):
    async with aiohttp.ClientSession() as s:
        if method == "GET":
            async with s.get(url, timeout=timeout) as r:
                return await r.json()
        else:
            async with s.post(url, json=payload, timeout=timeout) as r:
                return await r.json()

async def helius_get_tx(signature: str) -> dict:
    payload = {
        "jsonrpc":"2.0","id":1,"method":"getTransaction",
        "params":[signature, {"encoding":"jsonParsed","commitment":"confirmed"}]
    }
    return await _http_json(RPC_URL, method="POST", payload=payload)

async def get_block_time(signature: str) -> Optional[float]:
    j = await helius_get_tx(signature)
    bt = (j.get("result") or {}).get("blockTime")
    return float(bt) if bt is not None else None

async def get_account_info_jsonparsed(pubkey: str) -> dict:
    payload = {
        "jsonrpc":"2.0","id":1,"method":"getAccountInfo",
        "params":[pubkey, {"encoding":"jsonParsed","commitment":"confirmed"}]
    }
    j = await _http_json(RPC_URL, method="POST", payload=payload)
    return (j.get("result") or {}).get("value", {}) or {}

async def get_token_metadata(mint: str) -> dict:
    url = f"https://api.helius.xyz/v0/tokens/metadata?api-key={HELIUS_API_KEY}&mints[]={mint}"
    j = await _http_json(url)
    arr = (j or {}).get("tokens") or []
    return arr[0] if arr else {}

async def get_token_holders_count(mint: str) -> Optional[int]:
    # best-effort, может отсутствовать
    url = f"https://api.helius.xyz/v0/tokens/holders?api-key={HELIUS_API_KEY}&mint={mint}&page=1&limit=1"
    j = await _http_json(url)
    # Helius может возвращать total или придётся читать size другого вызова — учитываем оба варианта
    if isinstance(j, dict) and "total" in j:
        return int(j["total"])
    if isinstance(j, list):
        # если вернулся массив адресов, но limit=1 — тогда не узнаем total
        return None
    return None

def extract_mints_from_tx_json(tx_json: dict) -> list[str]:
    """Парсим jsonParsed транзу: ищем initializeMint/mintTo → собираем адреса mint."""
    res = []
    tx = tx_json.get("result")
    if not tx:
        return res

    # inner
    meta = tx.get("meta") or {}
    for group in (meta.get("innerInstructions") or []):
        for ix in group.get("instructions", []):
            parsed = ix.get("parsed") or {}
            if isinstance(parsed, dict) and parsed.get("type") in ("initializeMint","initializeMint2","mintTo"):
                mint = (parsed.get("info") or {}).get("mint")
                if mint:
                    res.append(mint)

    # top-level
    msg = tx.get("transaction", {}).get("message", {}) or {}
    for ix in (msg.get("instructions") or []):
        parsed = ix.get("parsed") or {}
        if isinstance(parsed, dict) and parsed.get("type") in ("initializeMint","initializeMint2","mintTo"):
            mint = (parsed.get("info") or {}).get("mint")
            if mint:
                res.append(mint)

    return list(dict.fromkeys(res))  # уникально, порядок сохранён


# ========= HONEYPOT CHECK =========
def _mint_risk_flags(parsed_acc: dict) -> list[str]:
    """Быстрые флаги: mintAuthority/freezeAuthority, Token-2022 transferHook/transferFee>10%."""
    risks = []
    info = (parsed_acc.get("data") or {}).get("parsed", {}).get("info", {}) or {}
    if info.get("mintAuthority"):
        risks.append("mintAuthority not revoked")
    if info.get("freezeAuthority"):
        risks.append("freezeAuthority set")
    ext = info.get("extensions") or {}
    if ext:
        if "transferHook" in ext:
            risks.append("Token2022 transferHook")
        tf = ext.get("transferFeeConfig") or {}
        bps = tf.get("transferFeeBasisPoints")
        if isinstance(bps, int) and bps > 1000:
            risks.append(f"transferFee {bps/100:.2f}%")
    return risks

async def jup_quote(mint_in: str, amount_in: int) -> Optional[dict]:
    url = f"{JUP_BASE}/quote?inputMint={mint_in}&outputMint={WSOL_MINT}&amount={amount_in}&slippageBps=100"
    q = await _http_json(url)
    if not q:
        return None
    if "outAmount" in q:
        return q
    if "routes" in q and q["routes"]:
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
    msg_b64 = ixs_resp.get("swapTransactionMessage")
    if not msg_b64:
        return (False, "no message from Jupiter")
    payload = {
        "jsonrpc":"2.0","id":1,"method":"simulateTransaction",
        "params":[
            msg_b64,
            {"encoding":"base64","sigVerify":False,"replaceRecentBlockhash":True,"commitment":"processed"}
        ]
    }
    j = await _http_json(RPC_URL, method="POST", payload=payload)
    err = (j.get("result") or {}).get("err")
    ok = err is None
    reason = "ok" if ok else f"simulate err: {err}"
    return (ok, reason)

async def honeypot_check(mint: str) -> Tuple[bool, str]:
    """True/ok → продажа симулируется, False/... → подозрение на honeypot."""
    parsed = await get_account_info_jsonparsed(mint)
    risks = _mint_risk_flags(parsed)
    if risks:
        return (False, " ; ".join(risks))

    info = (parsed.get("data") or {}).get("parsed", {}).get("info", {}) or {}
    try:
        supply = int(info.get("supply", "0"))
        dec    = int(info.get("decimals", 9))
    except Exception:
        supply, dec = 0, 9

    test_amount = max(supply // 10_000, 10 ** max(dec - 6, 0))  # ~0.01% от supply, но не меньше 1e-6
    if test_amount == 0:
        test_amount = 10 ** max(dec - 6, 0)

    quote = await jup_quote(mint, test_amount)
    if not quote:
        return (False, "no Jupiter route (no pool/liquidity)")
    ixs = await jup_swap_instructions(quote)
    if not ixs:
        return (False, "no swap-instructions")
    ok, reason = await helius_simulate(ixs)
    return (ok, reason)


# ========= PRICE (Jupiter live) =========
async def jup_price_spl_in_sol(mint: str, amount_in_atoms: Optional[int] = None) -> Optional[float]:
    """Цена 1 токена в SOL (через котировку Jupiter)."""
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


# ========= FILTERS PIPELINE & REPORT =========
async def evaluate_token(mint: str, signature: Optional[str]) -> tuple[bool, str, dict, Optional[float]]:
    """
    Возвращает: (passed_all, report_text, token_meta, entry_price_sol)
    """
    lines = []
    ok_all = True

    # Age
    now = time.time()
    created_sec = None
    if signature:
        bt = await get_block_time(signature)
        if bt:
            created_sec = bt
    if created_sec is None:
        lines.append("❌ Age: не удалось определить время блока")
        return (False, "\n".join(lines), {}, None)
    age = now - created_sec
    age_ok = age <= MAX_TOKEN_AGE_SEC
    lines.append(f"{'✅' if age_ok else '❌'} Age: {age:.1f}s (limit {MAX_TOKEN_AGE_SEC}s)")
    ok_all &= age_ok
    if not age_ok:
        return (False, "\n".join(lines), {}, None)

    # Honeypot
    hp_ok, hp_reason = await honeypot_check(mint)
    lines.append(f"{'✅' if hp_ok else '❌'} Honeypot: {hp_reason}")
    ok_all &= hp_ok
    if not hp_ok:
        return (False, "\n".join(lines), {}, None)

    # Metadata (soft)
    meta = await get_token_metadata(mint)

    # SellTax
    sell_tax = meta.get("sellTax")
    if isinstance(sell_tax, (int, float)):
        st_ok = float(sell_tax) <= MAX_SELL_TAX
        lines.append(f"{'✅' if st_ok else '❌'} SellTax: {sell_tax} (limit {MAX_SELL_TAX})")
        ok_all &= st_ok
        if not st_ok:
            return (False, "\n".join(lines), meta, None)

    # LP locked
    lp_locked = meta.get("lpLocked")
    if lp_locked is not None:
        lp_ok = bool(lp_locked)
        lines.append(f"{'✅' if lp_ok else '❌'} LP Locked: {lp_locked}")
        ok_all &= lp_ok
        if not lp_ok:
            return (False, "\n".join(lines), meta, None)

    # Creator share
    creator_hold = meta.get("creatorHold")
    if isinstance(creator_hold, (int, float)):
        ch_ok = float(creator_hold) <= MAX_CREATOR_HOLD
        lines.append(f"{'✅' if ch_ok else '❌'} Creator share: {creator_hold:.2f} (limit {MAX_CREATOR_HOLD})")
        ok_all &= ch_ok
        if not ch_ok:
            return (False, "\n".join(lines), meta, None)

    # Holders
    holders_count = await get_token_holders_count(mint)
    if holders_count is not None:
        h_ok = holders_count >= MIN_HOLDERS
        lines.append(f"{'✅' if h_ok else '❌'} Holders: {holders_count} (min {MIN_HOLDERS})")
        ok_all &= h_ok
        if not h_ok:
            return (False, "\n".join(lines), meta, None)
    else:
        lines.append("ℹ️ Holders: n/a")

    # Liquidity (если Helius прислал)
    liq = meta.get("liquidity")
    if isinstance(liq, (int, float)):
        l_ok = float(liq) >= MIN_LIQ_SOL
        lines.append(f"{'✅' if l_ok else '❌'} Liquidity: {liq} SOL (min {MIN_LIQ_SOL} SOL)")
        ok_all &= l_ok
        if not l_ok:
            return (False, "\n".join(lines), meta, None)
    else:
        lines.append("ℹ️ Liquidity: n/a")

    # Entry price (live) через Jupiter
    entry_price = await jup_price_spl_in_sol(mint)
    if entry_price is None:
        lines.append("❌ Price: нет маршрута на Jupiter (no quote)")
        return (False, "\n".join(lines), meta, None)
    lines.append(f"✅ Price (Jupiter): {entry_price:.10f} SOL")

    return (ok_all, "\n".join(lines), meta, entry_price)


# ========= MAIN LOOP (WS + parsing) =========
async def listen_pumpfun():
    backoff = 2
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                sub = {
                    "jsonrpc":"2.0","id":1,"method":"logsSubscribe",
                    "params":[{"mentions":[PUMPFUN_PROGRAM_ID]}, {"commitment":"finalized"}]
                }
                await ws.send(json.dumps(sub))
                print("🔌 Subscribed to Pump.fun logs via Helius")
                backoff = 2

                while True:
                    raw = await ws.recv()
                    msg = json.loads(raw)

                    if msg.get("method") != "logsNotification":
                        continue
                    value = msg.get("params", {}).get("result", {}).get("value", {})
                    signature = value.get("signature")
                    if not signature:
                        continue

                    # подтягиваем транзу и тащим mint'ы
                    tx_json = await helius_get_tx(signature)
                    mints = extract_mints_from_tx_json(tx_json)
                    if not mints:
                        continue

                    for mint in mints:
                        passed, report, meta, entry_price = await evaluate_token(mint, signature)
                        sym = meta.get("symbol") or meta.get("tokenSymbol") or "UNK"
                        name = meta.get("name") or "Unnamed"

                        header = (
                            f"<b>📢 Token candidate</b>\n"
                            f"Name: <b>{name}</b>\n"
                            f"Symbol: <b>{sym}</b>\n"
                            f"Mint: <code>{mint}</code>\n"
                            f"Sig: <code>{signature}</code>\n\n"
                            f"{report}\n\n"
                            f"<b>Verdict:</b> {'✅ BUY' if passed else '⚠️ RISK'}"
                        )

                        print(header)
                        send_message(header)

                        if passed and entry_price is not None:
                            # тестовая «покупка» (лог/телега), реальных свопов пока нет
                            deal.buy({"mint": mint, "symbol": sym}, entry_price, header)

        except Exception as e:
            print(f"⚠️ WS error: {e} — reconnecting in {backoff}s…")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
