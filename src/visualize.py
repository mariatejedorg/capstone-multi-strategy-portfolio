"""Visualización estática: curvas de capital comparadas (estrategia vs.
igual-ponderada buy & hold vs. benchmark), y nº de activos activos en cada
rebalanceo a lo largo del tiempo."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def plot_equity_curves(strategy_equity: pd.Series, equal_weight_equity: pd.Series,
                        benchmark_equity: pd.Series, benchmark_name: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(strategy_equity.index, strategy_equity.values, color="tab:blue", linewidth=2, label="Multi-estrategia (momentum + Markowitz)")
    ax.plot(equal_weight_equity.index, equal_weight_equity.values, color="tab:orange", linewidth=1.5, label="Igual-ponderada (buy & hold)")
    ax.plot(benchmark_equity.index, benchmark_equity.values, color="black", linewidth=1.2, linestyle="--", label=benchmark_name)

    ax.set_title("Curvas de capital: estrategia vs. referencias")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Capital (base 100)")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    OUTPUTS_DIR.mkdir(exist_ok=True)
    fig.savefig(OUTPUTS_DIR / "equity_curves.png", dpi=150)
    plt.close(fig)


def plot_active_assets(rebalance_log: list[dict]) -> None:
    dates = [entry["fecha"] for entry in rebalance_log]
    n_active = [len(entry["activos_activos"]) for entry in rebalance_log]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.step(dates, n_active, where="post", color="tab:blue", linewidth=1.5)
    ax.fill_between(dates, n_active, step="post", color="tab:blue", alpha=0.15)

    ax.set_title("Nº de activos con señal de momentum activa en cada rebalanceo")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Activos activos")
    ax.set_ylim(0, 8.5)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    OUTPUTS_DIR.mkdir(exist_ok=True)
    fig.savefig(OUTPUTS_DIR / "active_assets.png", dpi=150)
    plt.close(fig)
