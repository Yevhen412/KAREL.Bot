from Telegram import send_telegram_message

def simulate_trade(btc_direction, correlated_asset, asset_data, entry_index):
    entry_price = asset_data['close'][entry_index]

    # Настройки симуляции
    leverage = 3
    take_profit_pct = 0.0045  # 0.45%
    stop_loss_pct = 0.002     # 0.2%
    commission_pct = 0.002    # 0.2% round trip

    direction = "LONG" if btc_direction == "UP" else "SHORT"
    multiplier = 1 if direction == "LONG" else -1

    # Симуляция следующих свечей
    for i in range(entry_index + 1, len(asset_data)):
        high = asset_data['high'][i]
        low = asset_data['low'][i]

        target_price = entry_price * (1 + multiplier * take_profit_pct)
        stop_price = entry_price * (1 - multiplier * stop_loss_pct)

        # Условия выхода
        if direction == "LONG":
            if high >= target_price:
                exit_price = target_price
                result = "TP"
                break
            elif low <= stop_price:
                exit_price = stop_price
                result = "SL"
                break
        else:  # SHORT
            if low <= target_price:
                exit_price = target_price
                result = "TP"
                break
            elif high >= stop_price:
                exit_price = stop_price
                result = "SL"
                break
    else:
        exit_price = asset_data['close'].iloc[-1]
        result = "CLOSE"

    # Расчёт PnL
    gross_return = (exit_price - entry_price) * multiplier / entry_price
    pnl = gross_return * leverage - commission_pct
    pnl_usdt = round(pnl * 200, 2)  # на сумму $200

    # Отправка в Telegram
    message = (
        f"Симуляция сделки:\n"
        f"🔹 Актив: {correlated_asset}\n"
        f"🔹 Направление: {direction}\n"
        f"🔹 Entry: {entry_price:.2f}\n"
        f"🔹 Exit: {exit_price:.2f}\n"
        f"🔹 Результат: {result}\n"
        f"🔹 PnL: {pnl_usdt} USDT"
    )
    send_telegram_message(message)
