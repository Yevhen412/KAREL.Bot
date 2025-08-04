from Telegram import send_telegram_message

def simulate_trade(direction: str, entry_price: float, atr: float):
    if direction not in ["up", "down"]:
        send_telegram_message("⚠️ Направление неизвестно — сделка не открыта.")
        return

    trade_type = "LONG" if direction == "up" else "SHORT"

    if direction == "up":
        tp = entry_price + 0.5 * atr
        sl = entry_price - 0.25 * atr
    else:  # SHORT
        tp = entry_price - 0.5 * atr
        sl = entry_price + 0.25 * atr

    send_telegram_message(
        f"📊 Симулируем сделку:\n"
        f"Тип: {trade_type}\n"
        f"Цена входа: {entry_price:.2f}\n"
        f"TP: {tp:.2f} | SL: {sl:.2f} (ATR={atr:.2f})"
    )
