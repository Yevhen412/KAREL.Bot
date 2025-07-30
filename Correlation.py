import pandas as pd

def calculate_correlation(btc_df, other_assets: dict, period: int = 12) -> dict:
    """
    Вычисляет корреляцию BTC с другими монетами на основе процентных изменений.
    
    btc_df: DataFrame BTC с колонкой 'close'
    other_assets: {'ETH': df, 'SOL': df, 'XRP': df, 'ADA': df, 'AVAX': df} — словарь с DataFrame монет
    period: Кол-во последних свечей для расчёта (по умолчанию 12)
    """
    btc_returns = btc_df['close'].pct_change().tail(period)
    correlation_results = {}

    for symbol, df in other_assets.items():
        if 'close' not in df.columns or len(df) < period:
            continue
        asset_returns = df['close'].pct_change().tail(period)
        correlation = btc_returns.corr(asset_returns)
        correlation_results[symbol] = round(correlation, 4)

    return correlation_results
