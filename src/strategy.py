"""Estrategia multi-activo: combina la señal de momentum del Proyecto 2
(qué activos están "en juego") con la asignación de máximo Sharpe del
Proyecto 9 (cómo repartir el capital entre ellos). No hay lógica de señal
ni de optimización nueva aquí -- solo la orquestación de rebalanceo mensual
que une las dos piezas ya construidas y probadas por separado.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.multi_strategy import LOOKBACK_DAYS, RISK_FREE_RATE, SMA_LONG, SMA_SHORT, TRADING_DAYS_PER_YEAR


def _load_module(relative_project: str, module_filename: str, module_alias: str):
    """Carga un módulo de otro proyecto del portfolio por ruta de archivo,
    sin contaminar sys.path ni sys.modules con el paquete "config" de ese
    otro proyecto -- mismo mecanismo (y mismo motivo) ya construido en
    proyecto-6-opciones-volatilidad-implicita/src/monte_carlo_check.py y
    reutilizado en los Proyectos 7 y 8.
    """
    module_path = Path(__file__).resolve().parents[2] / relative_project / "src" / module_filename

    saved_config_modules = {
        name: mod for name, mod in sys.modules.items()
        if name == "config" or name.startswith("config.")
    }
    for name in saved_config_modules:
        del sys.modules[name]

    sys.path.insert(0, str(module_path.parent))
    try:
        spec = importlib.util.spec_from_file_location(module_alias, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(module_path.parent))
        for name in [n for n in sys.modules if n == "config" or n.startswith("config.")]:
            del sys.modules[name]
        sys.modules.update(saved_config_modules)

    return module


_signals = _load_module("proyecto-2-momentum-backtest", "signals.py", "proyecto2_signals")
_markowitz = _load_module("proyecto-9-markowitz-frontera-eficiente", "markowitz.py", "proyecto9_markowitz")


def compute_active_signals(prices: pd.DataFrame) -> pd.DataFrame:
    """Tabla booleana (fecha x activo): True si ese activo está "activo"
    (señal de momentum en mercado) ese día. Reutiliza moving_averages,
    compute_signal y tradeable_signal del Proyecto 2 columna a columna --
    el shift(1) de tradeable_signal es lo que evita el look-ahead bias
    (la señal del día t se decide con el cierre de t-1).
    """
    active = {}
    for ticker in prices.columns:
        mas = _signals.moving_averages(prices[ticker], short=SMA_SHORT, long=SMA_LONG)
        signal = _signals.compute_signal(mas)
        active[ticker] = _signals.tradeable_signal(signal).astype(bool)

    return pd.DataFrame(active)


def rebalance_dates(index: pd.DatetimeIndex, burn_in_days: int = SMA_LONG) -> list:
    """Primer día de cotización de cada mes, a partir de burn_in_days
    sesiones desde el principio del histórico (para que la SMA larga y la
    primera ventana de mu/Sigma ya tengan datos suficientes)."""
    usable_index = index[burn_in_days:]
    months = pd.Series(usable_index).dt.to_period("M")
    first_of_month = pd.Series(usable_index).groupby(months.values).first()
    return sorted(first_of_month.tolist())


def _weights_for_date(returns: pd.DataFrame, active_today: pd.Series, as_of: pd.Timestamp) -> pd.Series:
    """Decide los pesos para el periodo que empieza en `as_of`:

    - 0 activos activos: cartera en liquidez (todo a 0 -- simplificación
      explícita, se documenta en el README que esto asume retorno 0 en
      liquidez en vez de acumular el tipo libre de riesgo).
    - 1 activo activo: 100% ahí (Markowitz con un solo activo no tiene
      nada que optimizar).
    - >=2 activos activos: max_sharpe_portfolio del Proyecto 9, sobre
      mu/Sigma estimados con la ventana móvil de LOOKBACK_DAYS sesiones
      ANTERIORES a `as_of` (nunca datos futuros).
    """
    active_tickers = active_today[active_today].index.tolist()
    weights = pd.Series(0.0, index=returns.columns)

    if len(active_tickers) == 0:
        return weights

    if len(active_tickers) == 1:
        weights[active_tickers[0]] = 1.0
        return weights

    window = returns.loc[:as_of, active_tickers].tail(LOOKBACK_DAYS)
    mu = window.mean().to_numpy() * TRADING_DAYS_PER_YEAR
    Sigma = window.cov().to_numpy() * TRADING_DAYS_PER_YEAR

    optimal_weights = _markowitz.max_sharpe_portfolio(mu, Sigma, RISK_FREE_RATE)
    weights[active_tickers] = optimal_weights
    return weights


def backtest(prices: pd.DataFrame, active_signals: pd.DataFrame) -> tuple[pd.Series, list[dict]]:
    """Recorre las fechas de rebalanceo, decide los pesos en cada una, y
    encadena los retornos diarios ponderados de todo el periodo en una
    única serie -- la curva de retornos de la estrategia."""
    returns = np.log(prices / prices.shift(1)).dropna()
    dates = rebalance_dates(prices.index)

    strategy_returns = pd.Series(dtype=float)
    rebalance_log = []

    for i, start_date in enumerate(dates):
        end_date = dates[i + 1] if i + 1 < len(dates) else prices.index[-1]
        period_returns = returns.loc[start_date:end_date]
        if start_date in period_returns.index and i > 0:
            period_returns = period_returns.iloc[1:]  # evita solapar el último día del periodo anterior

        weights = _weights_for_date(returns, active_signals.loc[start_date], start_date)
        period_strategy_returns = period_returns @ weights

        strategy_returns = pd.concat([strategy_returns, period_strategy_returns])
        rebalance_log.append({
            "fecha": start_date,
            "activos_activos": [t for t in weights.index if weights[t] > 0],
            "pesos": weights[weights > 0].to_dict(),
        })

    return strategy_returns, rebalance_log


if __name__ == "__main__":
    # Verificación con un caso de juguete: 3 activos sintéticos, señales
    # controladas a mano, para comprobar que las reglas de asignación
    # (0 / 1 / >=2 activos activos) se cumplen exactamente.
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    returns_toy = pd.DataFrame({
        "A": [0.01, 0.02, -0.01, 0.00, 0.01],
        "B": [0.00, 0.01, 0.02, -0.01, 0.00],
        "C": [-0.01, 0.00, 0.01, 0.02, -0.01],
    }, index=dates)

    print("Caso: 0 activos activos ->", _weights_for_date(returns_toy, pd.Series({"A": False, "B": False, "C": False}), dates[-1]).to_dict())
    print("Caso: 1 activo activo   ->", _weights_for_date(returns_toy, pd.Series({"A": True, "B": False, "C": False}), dates[-1]).to_dict())
    print("Caso: 2 activos activos ->", _weights_for_date(returns_toy, pd.Series({"A": True, "B": True, "C": False}), dates[-1]).to_dict())
