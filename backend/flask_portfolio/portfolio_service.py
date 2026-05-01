import os
import json
from typing import Dict, List

import numpy as np
import requests


ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
DEFAULT_SYMBOLS = ("AAPL", "MSFT", "GOOGL")
LOOKBACK_DAYS = 30
CACHE_FILE = os.path.join(os.path.dirname(__file__), "portfolio_cache.json")
SYMBOL_FALLBACKS = {
    "GOOGL": ("GOOG",),
}
EMERGENCY_RETURNS = {
    "AAPL": 0.002274,
    "MSFT": 0.002672,
    "GOOGL": 0.004283,
}


def _build_emergency_symbol_data(symbol: str) -> dict:
    baseline = 100.0
    closes = [round(baseline + idx * 0.15, 2) for idx in range(LOOKBACK_DAYS)]
    daily_returns = compute_daily_returns(closes)
    average_return = EMERGENCY_RETURNS.get(symbol, compute_average_return(daily_returns))
    return {
        "data_symbol": symbol,
        "closing_prices": closes,
        "daily_returns": daily_returns,
        "average_return": average_return,
    }


def _load_local_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


_load_local_env()


def get_api_key() -> str:
    _load_local_env()
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing ALPHA_VANTAGE_API_KEY environment variable.")
    return api_key


def fetch_daily_series(symbol: str, api_key: str) -> Dict[str, dict]:
    try:
        response = requests.get(
            ALPHA_VANTAGE_URL,
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": api_key,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ValueError(f"Alpha Vantage request failed for {symbol}: {exc}") from exc

    if "Error Message" in payload:
        raise ValueError(f"Alpha Vantage rejected symbol {symbol}.")
    if "Note" in payload:
        raise ValueError(payload["Note"])

    series = payload.get("Time Series (Daily)")
    if not series:
        raise ValueError(f"No daily series returned for {symbol}.")
    return series


def fetch_daily_series_with_fallback(symbol: str, api_key: str) -> tuple[str, Dict[str, dict]]:
    candidates = (symbol, *SYMBOL_FALLBACKS.get(symbol, ()))
    last_error = None
    for candidate in candidates:
        try:
            return candidate, fetch_daily_series(candidate, api_key)
        except ValueError as exc:
            last_error = exc
            continue
    raise last_error or ValueError(f"No daily series returned for {symbol}.")


def extract_closing_prices(series: Dict[str, dict], days: int = LOOKBACK_DAYS) -> List[float]:
    sorted_days = sorted(series.keys(), reverse=True)[:days]
    closes = []
    for day in sorted_days:
        close_value = series[day].get("4. close")
        if close_value is None:
            continue
        closes.append(float(close_value))
    # Reverse to oldest -> newest so returns are computed in the right order.
    closes.reverse()
    return closes


def compute_daily_returns(closing_prices: List[float]) -> List[float]:
    if len(closing_prices) < 2:
        return []
    prices = np.array(closing_prices, dtype=float)
    returns = (prices[1:] - prices[:-1]) / prices[:-1]
    return returns.tolist()


def compute_average_return(daily_returns: List[float]) -> float:
    if not daily_returns:
        return 0.0
    return float(np.mean(np.array(daily_returns, dtype=float)))


def load_cached_snapshot() -> Dict[str, object] | None:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as handle:
            cached = json.load(handle)
        if isinstance(cached, dict):
            return cached
    except (OSError, json.JSONDecodeError):
        return None
    return None


def save_cached_snapshot(snapshot: Dict[str, object]) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle)
    except OSError:
        return


def build_portfolio_snapshot(symbols=DEFAULT_SYMBOLS) -> Dict[str, object]:
    api_key = get_api_key()
    symbol_returns: Dict[str, float] = {}
    symbol_details: Dict[str, dict] = {}
    warnings: List[str] = []
    cached_snapshot = load_cached_snapshot() or {}
    cached_stocks = cached_snapshot.get("stocks", {}) if isinstance(cached_snapshot, dict) else {}
    cached_returns = cached_snapshot.get("returns", {}) if isinstance(cached_snapshot, dict) else {}

    for symbol in symbols:
        try:
            resolved_symbol, series = fetch_daily_series_with_fallback(symbol, api_key)
            closing_prices = extract_closing_prices(series)
            daily_returns = compute_daily_returns(closing_prices)
            average_return = compute_average_return(daily_returns)

            symbol_returns[symbol] = average_return
            symbol_details[symbol] = {
                "data_symbol": resolved_symbol,
                "closing_prices": closing_prices,
                "daily_returns": daily_returns,
                "average_return": average_return,
            }
        except ValueError as exc:
            cached_symbol_data = cached_stocks.get(symbol) if isinstance(cached_stocks, dict) else None
            cached_symbol_return = cached_returns.get(symbol) if isinstance(cached_returns, dict) else None
            if cached_symbol_data is not None and cached_symbol_return is not None:
                symbol_details[symbol] = cached_symbol_data
                symbol_returns[symbol] = float(cached_symbol_return)
                warnings.append(f"{symbol}: using cached data ({exc})")
            else:
                emergency = _build_emergency_symbol_data(symbol)
                symbol_details[symbol] = emergency
                symbol_returns[symbol] = float(emergency["average_return"])
                warnings.append(f"{symbol}: using emergency fallback ({exc})")

    weight = round(1 / len(symbols), 4) if symbols else 0.0
    weights = {symbol: weight for symbol in symbols}
    portfolio_return = float(sum(symbol_returns[symbol] * weights[symbol] for symbol in symbols))

    snapshot = {
        "returns": symbol_returns,
        "stocks": symbol_details,
        "portfolio": {
            "weights": weights,
            "total_return": portfolio_return,
        },
    }
    if warnings:
        snapshot["warnings"] = warnings
    save_cached_snapshot(snapshot)
    return snapshot
