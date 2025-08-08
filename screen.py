import os
import json
import time
import asyncio
import requests
import websockets

API_KEY = os.getenv("HELIUS_API_KEY")
PROGRAM_ID = os.getenv("PUMPFUN_PROGRAM_ID")

WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={API_KEY}"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"

RECONNECT_BASE = 2  # секунды

class PumpScreen:
    def __init__(self, callback):
        if not API_KEY:
            raise RuntimeError("HELIUS_API_KEY не задан")
        if not PROGRAM_ID:
            raise RuntimeError("PUMPFUN_PROGRAM_ID не задан")
        self.callback = callback

    async def run(self):
        backoff = RECONNECT_BASE
        while True:
            try:
                async with websockets.connect(
                    WS_URL,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=4_000_000
                ) as ws:
                    # Подписка на логи программы Pump.fun
                    sub = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "logsSubscribe",
                        "params": [
                            {"mentions": [PROGRAM_ID]},
                            {"commitment": "finalized"}
                        ]
                    }
                    await ws.send(json.dumps(sub))
                    print("[screen] ✅ Подписались на логи Pump.fun")
                    backoff = RECONNECT_BASE

                    while True:
                        raw = await ws.recv()
                        msg = json.loads(raw)

                        if msg.get("method") != "logsNotification":
                            continue

                        value = msg.get("params", {}).get("result", {})
                        sig = value.get("value", {}).get("signature")
                        if not sig:
                            continue

                        # Достаём подробности транзы и вычленяем новые mint'ы
                        for mint in self._extract_mints(sig):
                            token = {
                                "mint": mint,
                                "tx": sig,
                                "ts": int(time.time())
                            }
                            await self.callback(token)

            except Exception as e:
                print(f"[screen] ⚠️ Соединение потеряно: {e}. Реконнект…")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    def _rpc(self, method, params):
        payload = {"jsonrpc":"2.0","id":1,"method":method,"params":params}
        r = requests.post(RPC_URL, json=payload, timeout=20)
        r.raise_for_status()
        return r.json()

    def _extract_mints(self, signature):
        """
        Тянем транзакцию в jsonParsed и ищем события initializeMint/mintTo.
        Возвращаем список адресов SPL-минтов.
        """
        try:
            res = self._rpc("getTransaction", [signature, {"encoding":"jsonParsed"}])
            tx = res.get("result")
            if not tx:
                return []

            mints = set()

            meta = tx.get("meta") or {}
            inner = meta.get("innerInstructions") or []
            for group in inner:
                for ix in group.get("instructions", []):
                    parsed = ix.get("parsed") or {}
                    if not isinstance(parsed, dict):
                        continue
                    typ = parsed.get("type")
                    if typ in ("initializeMint", "initializeMint2", "mintTo"):
                        info = parsed.get("info") or {}
                        mint = info.get("mint")
                        if mint:
                            mints.add(mint)

            # Подстраховка: верхний уровень инструкций
            message = tx.get("transaction", {}).get("message", {}) or {}
            for ix in (message.get("instructions") or []):
                parsed = ix.get("parsed") or {}
                if isinstance(parsed, dict):
                    typ = parsed.get("type")
                    if typ in ("initializeMint", "initializeMint2", "mintTo"):
                        info = parsed.get("info") or {}
                        mint = info.get("mint")
                        if mint:
                            mints.add(mint)

            return list(mints)
        except Exception as e:
            print(f"[screen] ⚠️ Не смогли разобрать транзу {signature}: {e}")
            return []
