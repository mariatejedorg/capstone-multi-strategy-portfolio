"""Punto de entrada: descarga precios reales, calcula la señal de momentum,
backtestea la estrategia multi-activo (momentum + Markowitz), la compara
contra una cartera igual-ponderada buy & hold y contra el benchmark, y
genera las visualizaciones.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.multi_strategy import BENCHMARK_NAME, BENCHMARK_TICKER, TICKERS

from data import get_prices, save_snapshot
from dashboard import build_dashboard
from strategy import _load_module, backtest, compute_active_signals, rebalance_dates
from visualize import plot_active_assets, plot_equity_curves

_metrics = _load_module("proyecto-2-momentum-backtest", "metrics.py", "proyecto2_metrics")


def _equity_curve(returns: pd.Series) -> pd.Series:
    """Curva de capital en base 100 a partir de una serie de retornos log diarios."""
    return 100 * np.exp(returns.cumsum())


def main() -> None:
    asset_names = list(TICKERS.keys())
    prices = get_prices(asset_names)
    save_snapshot(prices, "universe")

    benchmark_prices = get_prices([BENCHMARK_TICKER])
    save_snapshot(benchmark_prices, "benchmark")

    print("=== Datos descargados ===")
    print(f"Universo: {len(asset_names)} activos | Sesiones: {len(prices)}")

    active_signals = compute_active_signals(prices)
    strategy_returns, rebalance_log = backtest(prices, active_signals)
    strategy_equity = _equity_curve(strategy_returns)

    asset_returns = np.log(prices / prices.shift(1)).dropna()
    equal_weight_returns = asset_returns.loc[strategy_returns.index].mean(axis=1)
    equal_weight_equity = _equity_curve(equal_weight_returns)

    # El calendario bursátil de EEUU (benchmark) no coincide exactamente con
    # el europeo (universo invertible): festivos distintos (p. ej. el 4 de
    # julio cierra EEUU pero no Europa) dejan fechas en strategy_returns.index
    # que no existen en el índice del benchmark. reindex + fillna(0) trata
    # esos días como "el benchmark no se movió" -- una aproximación razonable
    # para un festivo de un solo mercado, y evita perder días de la comparación.
    benchmark_returns_full = np.log(benchmark_prices / benchmark_prices.shift(1)).dropna().iloc[:, 0]
    benchmark_returns = benchmark_returns_full.reindex(strategy_returns.index).fillna(0)
    benchmark_equity = _equity_curve(benchmark_returns)

    strategy_metrics = _metrics.performance_summary(strategy_returns, strategy_equity, "Multi-estrategia")
    equal_weight_metrics = _metrics.performance_summary(equal_weight_returns, equal_weight_equity, "Igual-ponderada")
    benchmark_metrics = _metrics.performance_summary(benchmark_returns, benchmark_equity, BENCHMARK_NAME)

    print(f"\n=== Backtest: {len(rebalance_log)} rebalanceos mensuales ===")
    print("\n=== Comparación de rendimiento (anualizado) ===")
    for m in (strategy_metrics, equal_weight_metrics, benchmark_metrics):
        print(f'{m["serie"]:>16}: retorno {m["rentabilidad_anualizada"]:+.2%} | '
              f'vol {m["volatilidad_anualizada"]:.2%} | Sharpe {m["sharpe_ratio"]:.2f} | '
              f'drawdown máx. {m["max_drawdown"]:.2%}')

    print("\n=== Últimos 3 rebalanceos ===")
    for entry in rebalance_log[-3:]:
        pesos = ", ".join(f"{TICKERS[t]}: {w:.1%}" for t, w in entry["pesos"].items())
        print(f'{entry["fecha"].date()}: {pesos or "(liquidez, 0 activos activos)"}')

    plot_equity_curves(strategy_equity, equal_weight_equity, benchmark_equity, BENCHMARK_NAME)
    plot_active_assets(rebalance_log)
    dashboard_path = build_dashboard(
        strategy_equity, equal_weight_equity, benchmark_equity, BENCHMARK_NAME, rebalance_log,
        strategy_metrics, equal_weight_metrics, benchmark_metrics,
    )

    print(f"\nGráficos guardados en outputs/ (dashboard interactivo: {dashboard_path})")


if __name__ == "__main__":
    main()
