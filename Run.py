import asyncio
from ATR import fetch_asset_candles, calculate_atr
from Step import analyze_candle
from Correlation import calculate_correlation
from Lag import detect_lag
from Deal import simulate_trade

simulate_trade(btc_direction, correlated_asset, asset_data, entry_index)

def main():
    print("Запуск стратегии...")
    
    atr = calculate_atr()
    btc_status = check_btc_step(atr)

    if btc_status is None:
        print("Свеча BTC не достигла 50% ATR — ожидание...")
        return
    
    btc_direction = btc_status['direction']
    entry_index = btc_status['index']  # индекс свечи для входа

    high_corr_assets = get_high_correlations()

    if not high_corr_assets:
        print("Нет активов с высокой корреляцией")
        return

    for asset, asset_data in high_corr_assets.items():
        if asset == "BTC":
            continue

        if find_lagging_asset(asset_data, entry_index, btc_direction):
            simulate_trade(btc_direction, asset, asset_data, entry_index)
            break  # одну сделку за проход
    else:
        print("Лагирующих активов не найдено")

if __name__ == "__main__":
    main()
