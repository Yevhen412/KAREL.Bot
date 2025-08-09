from datetime import datetime
from telegram import send_message

def buy(token: dict, entry_price_sol: float, report_text: str):
    """
    ТЕСТОВАЯ покупка: ничего не делает, только логирует и шлёт в Telegram.
    Когда будешь готов — здесь реальная покупка через Jupiter Swap.
    """
    now = datetime.now().strftime("%H:%M:%S")
    mint = token.get("mint")
    sym  = token.get("symbol") or token.get("tokenSymbol") or "UNK"

    msg = (
        f"🛒 <b>ТЕСТОВАЯ ПОКУПКА</b>\n"
        f"Token: <b>{sym}</b>\n"
        f"Mint: <code>{mint}</code>\n"
        f"Entry (Jupiter): <b>{entry_price_sol:.10f} SOL</b>\n"
        f"Time: {now}\n\n"
        f"{report_text}"
    )
    print(msg)
    send_message(msg)
