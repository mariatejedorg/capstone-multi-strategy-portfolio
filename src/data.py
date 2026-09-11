"""Descarga de precios históricos para varios tickers, un ticker por columna."""

import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.multi_strategy import HISTORICAL_PERIOD

# Mismo mecanismo que en los Proyectos 1-9: si un antivirus que inspecciona
# tráfico HTTPS (p. ej. Norton) rompe la verificación por defecto de yfinance,
# se usa un bundle de certificados local si existe.
_CUSTOM_CA_BUNDLE = Path(__file__).resolve().parent.parent / ".certs" / "cacert.pem"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _build_session():
    if not _CUSTOM_CA_BUNDLE.exists():
        return None
    from curl_cffi import requests as curl_requests

    return curl_requests.Session(impersonate="chrome", verify=str(_CUSTOM_CA_BUNDLE))


def get_prices(tickers: list[str], period: str = HISTORICAL_PERIOD) -> pd.DataFrame:
    """Precio de cierre ajustado diario para varios tickers, un ticker por columna."""
    raw = yf.download(tickers, period=period, auto_adjust=True, progress=False, session=_build_session())
    prices = raw["Close"]

    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])

    return prices.dropna(how="all").ffill().dropna()


def save_snapshot(prices: pd.DataFrame, name: str) -> Path:
    """Vuelca un DataFrame de precios a data/ como registro de la ejecución
    (no como caché de lectura)."""
    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / f"prices_{name}.csv"
    prices.to_csv(out_path)
    return out_path


if __name__ == "__main__":
    from config.multi_strategy import TICKERS

    prices = get_prices(list(TICKERS.keys()))
    print(f"Precios descargados: {prices.shape[0]} días x {prices.shape[1]} activos")
    print(prices.tail())
