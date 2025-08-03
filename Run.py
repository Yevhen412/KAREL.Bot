async def main():
    while True:
        try:
            # Ждём открытия новой свечи
            now = time.time()
            wait = 300 - (now % 300)
            send_telegram_message(f"⏳ Ждём открытия новой свечи: {int(wait)} сек...")
            await asyncio.sleep(wait)

            # 1. Получаем ATR по BTC
            btc_atr = await calculate_atr()
            send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")

            # 2. Следим за текущей 5-мин свечой
            candle_reached_threshold = False
            direction = None
            delta = 0

            while True:
                btc_df = await fetch_btc_candles()
                delta, direction = await analyze_candle(btc_df, btc_atr)

                if direction:
                    send_telegram_message(f"🟢 Δ: {delta:.2f} — достигнуто 50% ATR")
                    candle_reached_threshold = True
                    break
                else:
                    await asyncio.sleep(5)

            if not candle_reached_threshold:
                send_telegram_message("⛔️ Свеча не достигла 50% ATR — переходим к следующей.")
                continue

            # 3. Получаем данные по альтам
            alt_data = await fetch_alt_candles_batch(alt_symbols)
            correlations = calculate_correlation(btc_df, alt_data)
            lagging_coins = detect_lag(btc_df, alt_data, correlations)

            # 4. Совершаем сделки, если есть лагающие монеты
            if lagging_coins:
                for coin in lagging_coins:
                    simulate_trade(direction, coin)
            else:
                send_telegram_message("ℹ️ Лаг не обнаружен. Сделка не будет открыта.")

        except Exception as e:
            send_telegram_message(f"❌ Ошибка в основном цикле: {e}")

        # 5. Ждём до следующей свечи
        send_telegram_message("✅ Цикл завершён — ожидаем следующую 5-минутную свечу")
