def detect_lag(btc_df, other_assets: dict, top_symbols: list, threshold=0.0015):
    """
    Определяет наличие временного лага между BTC и наиболее скоррелированными активами.
    
    btc_df: DataFrame с данными по BTC
    other_assets: словарь {symbol: df} с остальными монетами
    top_symbols: список тикеров с наибольшей корреляцией
    threshold: порог изменения цены (по умолчанию 0.15%)

    Возвращает: тикер монеты с лагом или None
    """
    btc_change = btc_df['close'].iloc[-1] / btc_df['close'].iloc[-2] - 1

    for symbol in top_symbols:
        df = other_assets[symbol]
        alt_change = df['close'].iloc[-1] / df['close'].iloc[-2] - 1

        # Проверка: BTC вырос, а монета нет (или значительно меньше)
        if btc_change > threshold and alt_change < threshold / 2:
            print(f"Обнаружен лаг: {symbol}")
            return symbol

    print("Лаг не обнаружен. Сделка не будет открыта.")
    return None
