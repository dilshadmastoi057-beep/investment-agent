import sqlite3
import datetime
import os
import math
import json
import urllib.request
import time
import argparse
from html.parser import HTMLParser
import re

# DATABASE
DB_PATH = os.path.join(os.path.dirname(__file__), "stocks.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS stocks_data (
    symbol TEXT,
    price REAL,
    volume INTEGER,
    timestamp TEXT
)
""")
conn.commit()

# MANUAL PSX SYMBOLS (no external API)
PSX_SYMBOLS = [
    "HBL.KA",
    "OGDC.KA",
    "MCB.KA",
    "UBL.KA",
    "PPL.KA",
    "PSO.KA",
    "TRG.KA",
    "FATIMA.KA"
]

POCKET_PORTFOLIO_URL = os.getenv(
    "POCKET_PORTFOLIO_PSX_URL",
    "https://www.pocketportfolio.app/api/tickers/PSX/json"
)
POCKET_PORTFOLIO_SYMBOL_URL = os.getenv(
    "POCKET_PORTFOLIO_SYMBOL_URL",
    "https://www.pocketportfolio.app/api/tickers/{symbol}/json"
)
CACHE_KSE100_PATH = os.path.join(os.path.dirname(__file__), "kse100_cache.json")
KSE100_CACHE_TTL_SECONDS = int(os.getenv("KSE100_CACHE_TTL_SECONDS", "21600"))
KSE100_LIMIT = int(os.getenv("KSE100_LIMIT", "100"))
KSE100_SYMBOLS_FILE = os.getenv(
    "KSE100_SYMBOLS_FILE",
    os.path.join(os.path.dirname(__file__), "kse100_symbols.csv")
)
USE_EXTERNAL_FEED = os.getenv("USE_EXTERNAL_FEED", "1").lower() in ("1", "true", "yes")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "psx_cache.json")
CACHE_TTL_SECONDS = int(os.getenv("PSX_CACHE_TTL_SECONDS", "900"))
MAX_RETRIES = int(os.getenv("PSX_MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = float(os.getenv("PSX_RETRY_DELAY_SECONDS", "2.0"))
RETENTION_DAYS = int(os.getenv("STOCKS_RETENTION_DAYS", "365"))

# MUTUAL FUNDS / NAV INGESTION
FUND_API_URL = os.getenv("MUTUAL_FUND_API_URL", "https://example.com/api/funds")
FUNDS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "funds_cache.json")
FUNDS_CACHE_TTL_SECONDS = int(os.getenv("FUNDS_CACHE_TTL_SECONDS", "21600"))

def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as handle:
            cache = json.load(handle)
        ts = cache.get("fetched_at")
        if not ts:
            return None
        fetched_at = datetime.datetime.fromisoformat(ts)
        if (datetime.datetime.now() - fetched_at).total_seconds() > CACHE_TTL_SECONDS:
            return None
        return cache.get("data")
    except Exception:
        return None

def _save_cache(data):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as handle:
            json.dump(
                {"fetched_at": datetime.datetime.now().isoformat(), "data": data},
                handle
            )
    except Exception:
        pass

def _load_funds_cache():
    if not os.path.exists(FUNDS_CACHE_PATH):
        return None
    try:
        with open(FUNDS_CACHE_PATH, "r", encoding="utf-8") as handle:
            cache = json.load(handle)
        ts = cache.get("fetched_at")
        if not ts:
            return None
        fetched_at = datetime.datetime.fromisoformat(ts)
        if (datetime.datetime.now() - fetched_at).total_seconds() > FUNDS_CACHE_TTL_SECONDS:
            return None
        return cache.get("funds")
    except Exception:
        return None

def _save_funds_cache(funds):
    try:
        with open(FUNDS_CACHE_PATH, "w", encoding="utf-8") as handle:
            json.dump({"fetched_at": datetime.datetime.now().isoformat(), "funds": funds}, handle)
    except Exception:
        pass

def compute_fund_metrics(fund_history):
    """Compute simple metrics for a fund given its NAV history list of {'date','nav'} sorted ascending."""
    if not fund_history or len(fund_history) < 2:
        return {"expected_return": 0.0, "volatility": 0.0, "drawdown": 0.0, "latest_nav": None}
    # ensure sorted by date
    try:
        fund_history_sorted = sorted(fund_history, key=lambda x: x.get("date"))
    except Exception:
        fund_history_sorted = fund_history
    navs = []
    for item in fund_history_sorted:
        try:
            navs.append(float(item.get("nav")))
        except Exception:
            continue
    if len(navs) < 2:
        return {"expected_return": 0.0, "volatility": 0.0, "drawdown": 0.0, "latest_nav": navs[-1] if navs else None}
    returns = []
    peak = navs[0]
    max_dd = 0.0
    for i in range(1, len(navs)):
        prev = navs[i-1]
        cur = navs[i]
        if prev <= 0:
            continue
        returns.append(cur / prev - 1)
        if cur > peak:
            peak = cur
        if peak > 0:
            dd = (peak - cur) / peak
            if dd > max_dd:
                max_dd = dd
    mean_ret = statistics.mean(returns) if returns else 0.0
    vol = statistics.stdev(returns) if len(returns) > 1 else 0.0
    return {"expected_return": mean_ret, "volatility": vol, "drawdown": max_dd, "latest_nav": navs[-1]}

def fetch_mutual_funds():
    """Fetch mutual fund NAV time-series from configured API and return computed metrics per fund.
    Expected API shape: [{"symbol": "FUND1", "history": [{"date": "YYYY-MM-DD", "nav": 10.5}, ...]}, ...]
    """
    cached = _load_funds_cache()
    if cached:
        return cached
    payload = _fetch_json(FUND_API_URL)
    if not payload:
        return []
    funds = []
    for item in payload:
        symbol = item.get("symbol") or item.get("ticker")
        history = item.get("history") or item.get("nav_history") or []
        metrics = compute_fund_metrics(history)
        funds.append({
            "symbol": symbol,
            "history_length": len(history),
            "latest_nav": metrics.get("latest_nav"),
            "expected_return": metrics.get("expected_return"),
            "volatility": metrics.get("volatility"),
            "drawdown": metrics.get("drawdown")
        })
    _save_funds_cache(funds)
    return funds

class _KSE100Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.current = []
        self.rows = []
        self.capture = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        if self.in_table and tag == "tr":
            self.in_row = True
            self.current = []
        if self.in_row and tag in ("td", "th"):
            self.capture = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.capture = False
        if tag == "tr" and self.in_row:
            if self.current:
                self.rows.append(self.current)
            self.in_row = False
        if tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.capture:
            text = data.strip()
            if text:
                self.current.append(text)

def _load_kse100_cache():
    if not os.path.exists(CACHE_KSE100_PATH):
        return None
    try:
        with open(CACHE_KSE100_PATH, "r", encoding="utf-8") as handle:
            cache = json.load(handle)
        ts = cache.get("fetched_at")
        if not ts:
            return None
        fetched_at = datetime.datetime.fromisoformat(ts)
        if (datetime.datetime.now() - fetched_at).total_seconds() > KSE100_CACHE_TTL_SECONDS:
            return None
        return cache.get("symbols")
    except Exception:
        return None

def _save_kse100_cache(symbols):
    try:
        with open(CACHE_KSE100_PATH, "w", encoding="utf-8") as handle:
            json.dump(
                {"fetched_at": datetime.datetime.now().isoformat(), "symbols": symbols},
                handle
            )
    except Exception:
        pass

def _base_price(symbol):
    return 180 + (abs(hash(symbol)) % 220)

def _normalize_symbol(symbol):
    if "." in symbol:
        return symbol
    return f"{symbol}.KA"

def _price_for_day(symbol, day_index):
    base = _base_price(symbol)
    seasonal = 12 * math.sin(day_index / 6.0)
    trend = 0.25 * day_index
    noise = (abs(hash(f"{symbol}-{day_index}")) % 8) - 4
    return max(20.0, base + seasonal + trend + noise)

def fetch_psx_data(timestamp):
    data = []
    day_index = int(timestamp.strftime("%j"))
    for sym in PSX_SYMBOLS:
        data.append({
            "symbol": sym,
            "price": round(_price_for_day(sym, day_index), 2),
            "volume": 1000 + abs(hash(f"{sym}-{day_index}")) % 5000,
            "timestamp": timestamp.isoformat()
        })
    return data

def fetch_psx_data_for_symbols(timestamp, symbols):
    data = []
    day_index = int(timestamp.strftime("%j"))
    for sym in symbols:
        data.append({
            "symbol": _normalize_symbol(sym),
            "price": round(_price_for_day(sym, day_index), 2),
            "volume": 1000 + abs(hash(f"{sym}-{day_index}")) % 5000,
            "timestamp": timestamp.isoformat()
        })
    return data

def _fetch_json(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            if attempt == MAX_RETRIES:
                return None
            time.sleep(RETRY_DELAY_SECONDS)
    return None

def fetch_kse100_symbols():
    if os.path.exists(KSE100_SYMBOLS_FILE):
        try:
            with open(KSE100_SYMBOLS_FILE, "r", encoding="utf-8") as handle:
                symbols = []
                for line in handle:
                    value = line.strip().split(",")[0].strip()
                    if value and value.lower() != "symbol":
                        symbols.append(value)
                symbols = sorted(set(symbols))[:KSE100_LIMIT]
                if symbols:
                    return symbols
        except Exception as exc:
            print(f"Failed to read {KSE100_SYMBOLS_FILE}: {exc}")
    cached = _load_kse100_cache()
    if cached:
        return cached
    url = "https://dps.psx.com.pk/indices/KSE100"
    html = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                html = response.read().decode("utf-8", errors="ignore")
            break
        except Exception:
            if attempt == MAX_RETRIES:
                return []
            time.sleep(RETRY_DELAY_SECONDS)
    parser = _KSE100Parser()
    parser.feed(html or "")
    rows = parser.rows
    symbols = []
    if rows:
        header = rows[0]
        for row in rows[1:]:
            if len(row) < 2:
                continue
            entry = dict(zip(header, row))
            for key in entry.keys():
                if key.lower() in ("symbol", "symbol code", "company", "company code", "ticker"):
                    value = entry.get(key)
                    if value:
                        symbols.append(value.strip())
                    break
    if not symbols:
        matches = re.findall(r"<tr>\s*<td>\s*([A-Z]{2,})\s*</td>\s*<td>", html or "", re.IGNORECASE)
        symbols = [m.upper() for m in matches]
    symbols = sorted(set(symbols))[:KSE100_LIMIT]
    _save_kse100_cache(symbols)
    return symbols

def fetch_psx_from_pocket_portfolio():
    cached = _load_cache()
    if cached:
        return cached
    payload = _fetch_json(POCKET_PORTFOLIO_URL)
    if not payload:
        return []
    history = payload.get("history_sample") or []
    rows = []
    for item in history:
        symbol = item.get("symbol")
        price = item.get("close") or item.get("price")
        volume = item.get("volume") or 0
        timestamp = item.get("timestamp") or payload.get("timestamp")
        if not symbol or price is None:
            continue
        try:
            rows.append({
                "symbol": symbol,
                "price": float(price),
                "volume": int(float(volume)),
                "timestamp": str(timestamp)
            })
        except ValueError:
            continue
    _save_cache(rows)
    return rows

def fetch_psx_symbol_data(symbols):
    rows = []
    total = len(symbols)
    for idx, sym in enumerate(symbols, start=1):
        if total >= 20 and idx % 10 == 0:
            print(f"Fetching {idx}/{total} symbols...")
        clean = sym.replace(".KA", "").replace(".PSX", "")
        url = POCKET_PORTFOLIO_SYMBOL_URL.format(symbol=clean)
        payload = _fetch_json(url)
        if not payload:
            continue
        history = payload.get("history_sample") or []
        for item in history:
            price = item.get("close") or item.get("price")
            volume = item.get("volume") or 0
            timestamp = item.get("timestamp") or payload.get("timestamp")
            if price is None:
                continue
            try:
                rows.append({
                    "symbol": _normalize_symbol(sym),
                    "price": float(price),
                    "volume": int(float(volume)),
                    "timestamp": str(timestamp)
                })
            except ValueError:
                continue
    return rows

def save_to_db(data):
    for item in data:
        cursor.execute("""
        INSERT INTO stocks_data (symbol, price, volume, timestamp)
        VALUES (?, ?, ?, ?)
        """, (item["symbol"], item["price"], item["volume"], item["timestamp"]))
    conn.commit()

def cleanup_old_records():
    cutoff = datetime.datetime.now() - datetime.timedelta(days=RETENTION_DAYS)
    cursor.execute("DELETE FROM stocks_data WHERE timestamp < ?", (cutoff.isoformat(),))
    conn.commit()

def seed_history(days=60, symbols=None):
    cursor.execute("SELECT COUNT(*) FROM stocks_data")
    count = cursor.fetchone()[0]
    if count > 0:
        return
    start = datetime.datetime.now() - datetime.timedelta(days=days)
    for day_index in range(days):
        ts = start + datetime.timedelta(days=day_index)
        # Generate synthetic data with proper sequential trending
        if symbols:
            data = fetch_psx_data_for_symbols(ts, symbols)
            # Override prices to use sequential day_index instead of day-of-year
            for item in data:
                item["price"] = round(_price_for_day_sequential(item["symbol"], day_index), 2)
            save_to_db(data)
        else:
            data = fetch_psx_data(ts)
            for item in data:
                item["price"] = round(_price_for_day_sequential(item["symbol"], day_index), 2)
            save_to_db(data)

def _price_for_day_sequential(symbol, day_index):
    """Generate synthetic price using sequential day index (not day-of-year)"""
    base = _base_price(symbol)
    seasonal = 12 * math.sin(day_index / 6.0)
    trend = 0.25 * day_index
    noise = (abs(hash(f"{symbol}-{day_index}")) % 8) - 4
    return max(20.0, base + seasonal + trend + noise)

def run_pipeline():
    kse_symbols = fetch_kse100_symbols()
    if kse_symbols:
        seed_history(symbols=kse_symbols)
    else:
        seed_history()
    now = datetime.datetime.now()
    source = "pocket"
    if kse_symbols:
        if USE_EXTERNAL_FEED:
            data = fetch_psx_symbol_data(kse_symbols)
            source = "kse100"
        else:
            data = []
            source = "synthetic_kse100"
        if not data:
            data = fetch_psx_data_for_symbols(now, kse_symbols)
            source = "synthetic_kse100"
    else:
        if USE_EXTERNAL_FEED:
            data = fetch_psx_from_pocket_portfolio()
        else:
            data = []
        if not data:
            data = fetch_psx_symbol_data(PSX_SYMBOLS) if USE_EXTERNAL_FEED else []
            source = "manual_feed"
            if not data:
                data = fetch_psx_data(now)
                source = "synthetic_manual"
    save_to_db(data)
    cleanup_old_records()
    if source in ("manual_feed", "synthetic_manual") and not os.path.exists(KSE100_SYMBOLS_FILE):
        print("KSE-100 list not available. Add symbols file at:")
        print(f"  {KSE100_SYMBOLS_FILE}")
    if source.startswith("synthetic"):
        print("External data unavailable. Generated synthetic prices for coverage.")
    print(f"Saved {len(data)} records at {now.isoformat()} (source: {source})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true", help="Run pipeline on an interval.")
    parser.add_argument("--interval-minutes", type=int, default=1440)
    parser.add_argument("--fetch-funds", action="store_true", help="Fetch mutual funds NAVs and exit.")
    args = parser.parse_args()

    if args.schedule:
        while True:
            run_pipeline()
            time.sleep(max(60, args.interval_minutes * 60))
    else:
        if args.fetch_funds:
            funds = fetch_mutual_funds()
            print(f"Fetched {len(funds)} funds")
        else:
            run_pipeline()

