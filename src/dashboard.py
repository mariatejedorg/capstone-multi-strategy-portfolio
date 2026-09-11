"""Dashboard HTML interactivo con Plotly: un único archivo autocontenido en
outputs/. Mismos tokens de color y helpers de layout que
proyecto-9-markowitz-frontera-eficiente/src/dashboard.py, copiados
literalmente para dar continuidad visual entre proyectos del portfolio.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

BLUE = "#2a78d6"
ORANGE = "#e3a648"
INK_BLACK = "#0b0b0b"

SURFACE = "#fcfcfb"
PAGE_PLANE = "#f9f9f7"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
BORDER = "rgba(11,11,11,0.10)"

FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def _base_layout(title: str, **extra) -> dict:
    layout = dict(
        title=dict(text=title, font=dict(family=FONT_FAMILY, size=15, color=INK_PRIMARY)),
        font=dict(family=FONT_FAMILY, size=12, color=INK_SECONDARY),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        legend=dict(font=dict(color=INK_SECONDARY, size=11), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=50, r=30, t=50, b=40),
    )
    layout.update(extra)
    return layout


def _axis(**extra) -> dict:
    axis = dict(
        gridcolor=GRIDLINE,
        gridwidth=1,
        linecolor=BASELINE,
        tickfont=dict(color=INK_MUTED, size=11),
        title_font=dict(color=INK_SECONDARY, size=12),
        zeroline=False,
    )
    axis.update(extra)
    return axis


def _equity_figure(strategy_equity: pd.Series, equal_weight_equity: pd.Series,
                    benchmark_equity: pd.Series, benchmark_name: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=strategy_equity.index, y=strategy_equity.values, mode="lines",
                              name="Multi-estrategia", line=dict(color=BLUE, width=2.5)))
    fig.add_trace(go.Scatter(x=equal_weight_equity.index, y=equal_weight_equity.values, mode="lines",
                              name="Igual-ponderada (buy & hold)", line=dict(color=ORANGE, width=1.8)))
    fig.add_trace(go.Scatter(x=benchmark_equity.index, y=benchmark_equity.values, mode="lines",
                              name=benchmark_name, line=dict(color=INK_BLACK, width=1.3, dash="dash")))

    fig.update_layout(
        **_base_layout(
            "Curvas de capital: estrategia vs. referencias",
            xaxis=_axis(title="Fecha"),
            yaxis=_axis(title="Capital (base 100)"),
            hovermode="x unified",
            hoverlabel=dict(bgcolor=SURFACE, font=dict(color=INK_PRIMARY, family=FONT_FAMILY)),
            height=450,
        )
    )
    return fig


def _active_assets_figure(rebalance_log: list[dict]) -> go.Figure:
    dates = [entry["fecha"] for entry in rebalance_log]
    n_active = [len(entry["activos_activos"]) for entry in rebalance_log]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=n_active, mode="lines", line_shape="hv",
                              fill="tozeroy", fillcolor="rgba(42,120,214,0.15)", line=dict(color=BLUE, width=1.8)))

    fig.update_layout(
        **_base_layout(
            "Nº de activos con señal de momentum activa",
            xaxis=_axis(title="Fecha"),
            yaxis=_axis(title="Activos activos", range=[0, 8.5]),
            height=320,
        )
    )
    return fig


def _stat_tile(label: str, value: str, sublabel: str) -> str:
    return f"""<div class="tile">
  <div class="tile-label">{label}</div>
  <div class="tile-value">{value}</div>
  <div class="tile-sublabel">{sublabel}</div>
</div>"""


def _kpi_tiles_html(strategy_metrics: dict, equal_weight_metrics: dict, benchmark_metrics: dict) -> str:
    tiles = [
        _stat_tile("Multi-estrategia — retorno/riesgo", f'{strategy_metrics["rentabilidad_anualizada"]*100:.1f}% / {strategy_metrics["volatilidad_anualizada"]*100:.1f}%', f'Sharpe {strategy_metrics["sharpe_ratio"]:.2f} · DD máx. {strategy_metrics["max_drawdown"]*100:.1f}%'),
        _stat_tile("Igual-ponderada — retorno/riesgo", f'{equal_weight_metrics["rentabilidad_anualizada"]*100:.1f}% / {equal_weight_metrics["volatilidad_anualizada"]*100:.1f}%', f'Sharpe {equal_weight_metrics["sharpe_ratio"]:.2f} · DD máx. {equal_weight_metrics["max_drawdown"]*100:.1f}%'),
        _stat_tile("Benchmark — retorno/riesgo", f'{benchmark_metrics["rentabilidad_anualizada"]*100:.1f}% / {benchmark_metrics["volatilidad_anualizada"]*100:.1f}%', f'Sharpe {benchmark_metrics["sharpe_ratio"]:.2f} · DD máx. {benchmark_metrics["max_drawdown"]*100:.1f}%'),
    ]
    return '<div class="tiles">' + "".join(tiles) + "</div>"


def build_dashboard(
    strategy_equity: pd.Series, equal_weight_equity: pd.Series, benchmark_equity: pd.Series,
    benchmark_name: str, rebalance_log: list[dict],
    strategy_metrics: dict, equal_weight_metrics: dict, benchmark_metrics: dict,
) -> Path:
    equity_html = pio.to_html(
        _equity_figure(strategy_equity, equal_weight_equity, benchmark_equity, benchmark_name),
        full_html=False, include_plotlyjs="cdn", config={"displaylogo": False},
    )
    active_html = pio.to_html(
        _active_assets_figure(rebalance_log), full_html=False, include_plotlyjs=False, config={"displaylogo": False},
    )
    tiles_html = _kpi_tiles_html(strategy_metrics, equal_weight_metrics, benchmark_metrics)

    page = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Proyecto 10 — Capstone: Multi-Strategy Portfolio</title>
<style>
  :root {{
    --surface: {SURFACE};
    --page-plane: {PAGE_PLANE};
    --ink-primary: {INK_PRIMARY};
    --ink-secondary: {INK_SECONDARY};
    --ink-muted: {INK_MUTED};
    --gridline: {GRIDLINE};
    --border: {BORDER};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: {FONT_FAMILY};
    margin: 0;
    background: var(--page-plane);
    color: var(--ink-primary);
  }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 0 24px 64px; }}

  .hero {{
    background: linear-gradient(135deg, #123a2e 0%, #1baf7a 100%);
    color: #ffffff;
    padding: 48px 24px 40px;
    margin-bottom: 28px;
  }}
  .hero-inner {{ max-width: 1080px; margin: 0 auto; }}
  .hero h1 {{ font-size: 1.75rem; margin: 0 0 8px; font-weight: 700; }}
  .hero p {{ margin: 0; color: rgba(255,255,255,0.85); font-size: 0.95rem; }}
  .hero .meta {{ margin-top: 18px; font-size: 0.8rem; color: rgba(255,255,255,0.65); letter-spacing: 0.02em; }}

  .tiles {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
    margin: 0 0 28px;
  }}
  .tile {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
  }}
  .tile-label {{ font-size: 0.72rem; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; }}
  .tile-value {{ font-size: 1.45rem; font-weight: 700; color: var(--ink-primary); margin: 6px 0 2px; }}
  .tile-sublabel {{ font-size: 0.8rem; color: var(--ink-secondary); }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 22px;
  }}
  .card h2 {{ font-size: 1.05rem; margin: 0 0 16px; color: var(--ink-primary); font-weight: 600; }}

  footer {{ text-align: center; font-size: 0.78rem; color: var(--ink-muted); padding-top: 8px; }}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-inner">
    <h1>Capstone: Multi-Strategy Portfolio</h1>
    <p>Momentum (Proyecto 2) decide qué activos están en juego; Markowitz (Proyecto 9) decide cómo repartir el capital entre ellos. Backtest real, rebalanceo mensual, sobre 8 acciones europeas.</p>
    <div class="meta">Datos en vivo vía yfinance · integra los Proyectos 2 y 9 sin duplicar su lógica</div>
  </div>
</div>

<div class="wrap">

{tiles_html}

<div class="card">
  <h2>Curvas de capital</h2>
  {equity_html}
</div>

<div class="card">
  <h2>Activos en juego a lo largo del tiempo</h2>
  {active_html}
</div>

<footer>Proyecto 10 · Roadmap Quant · Python (numpy, scipy, pandas, yfinance, Plotly)</footer>

</div>
</body>
</html>"""

    OUTPUTS_DIR.mkdir(exist_ok=True)
    out_path = OUTPUTS_DIR / "dashboard.html"
    out_path.write_text(page, encoding="utf-8")
    return out_path
