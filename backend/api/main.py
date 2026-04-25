from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import datetime
import statistics
import hashlib
import secrets
import json
import io
import csv
import subprocess
import sys
import urllib.request
from html.parser import HTMLParser

app = FastAPI()

REPORTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data_pipeline", "equity_reports.json"
)
REPORTS_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data_pipeline", "equity_reports.csv"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db_path = os.path.join(os.path.dirname(__file__), "..", "data_pipeline", "stocks.db")
    return sqlite3.connect(db_path)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rating INTEGER,
        comments TEXT,
        created_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT,
        salt TEXT,
        created_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_portfolios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        profile_json TEXT,
        recommendation_json TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

class UserProfile(BaseModel):
    age: int
    income: float
    investment_amount: float
    risk_preference: str
    time_period_years: float
    financial_goals: str

def _risk_score(profile: UserProfile):
    pref = profile.risk_preference.strip().lower()
    if pref == "low":
        base = 0.2
    elif pref == "high":
        base = 0.8
    else:
        base = 0.5
    age_adjust = max(0.0, min(1.0, (50 - profile.age) / 50.0))
    time_adjust = max(0.0, min(1.0, profile.time_period_years / 10.0))
    income_adjust = max(0.0, min(1.0, profile.income / 200000.0))
    goal = profile.financial_goals.strip().lower()
    goal_adjust = 0.15 if "growth" in goal or "wealth" in goal else 0.0
    score = 0.45 * base + 0.2 * age_adjust + 0.2 * time_adjust + 0.1 * income_adjust + goal_adjust
    return max(0.0, min(1.0, score))

def _risk_level(score):
    if score < 0.35:
        return "Low"
    if score < 0.7:
        return "Medium"
    return "High"

def _parse_timestamp(value):
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None

def _group_prices(rows):
    grouped = {}
    for symbol, price, timestamp in rows:
        ts = _parse_timestamp(timestamp)
        if not ts:
            continue
        grouped.setdefault(symbol, []).append((ts, price))
    for symbol in grouped:
        grouped[symbol].sort(key=lambda x: x[0])
    return grouped

def _returns_for_prices(prices):
    returns = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        cur = prices[i]
        if prev <= 0:
            continue
        returns.append(cur / prev - 1)
    return returns

def _portfolio_stats(rows):
    grouped = _group_prices(rows)
    symbol_stats = {}
    returns_map = {}
    for symbol, data in grouped.items():
        prices = [p for _, p in data]
        returns = _returns_for_prices(prices)
        returns_map[symbol] = returns
        if len(returns) < 2:
            mean_ret = 0.0
            vol = 0.0
        else:
            mean_ret = statistics.mean(returns)
            vol = statistics.stdev(returns)
        drawdown = _max_drawdown(prices)
        symbol_stats[symbol] = {
            "expected_return": mean_ret,
            "volatility": vol,
            "drawdown": drawdown
        }
    return symbol_stats, returns_map

def _max_drawdown(prices):
    if not prices:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for price in prices:
        if price > peak:
            peak = price
        if peak > 0:
            dd = (peak - price) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd

def _market_returns(returns_map):
    if not returns_map:
        return []
    lengths = [len(r) for r in returns_map.values() if r]
    if not lengths:
        return []
    min_len = min(lengths)
    if min_len < 2:
        return []
    market = []
    symbols = [s for s, r in returns_map.items() if len(r) >= min_len]
    for i in range(min_len):
        vals = [returns_map[s][i] for s in symbols]
        market.append(statistics.mean(vals))
    return market

def _beta(symbol_returns, market_returns):
    if len(symbol_returns) < 2 or len(market_returns) < 2:
        return 1.0
    min_len = min(len(symbol_returns), len(market_returns))
    x = symbol_returns[:min_len]
    y = market_returns[:min_len]
    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / (min_len - 1)
    var = statistics.stdev(y) ** 2
    if var == 0:
        return 1.0
    return cov / var

def _optimize_portfolio(symbol_stats, risk_score, fundamental_scores=None):
    fundamental_scores = fundamental_scores or {}
    raw_scores = {}
    for symbol, stats in symbol_stats.items():
        exp_r = stats["expected_return"]
        vol = stats["volatility"]
        dd = stats.get("drawdown", 0.0)
        f_score = fundamental_scores.get(symbol, 0.0)
        raw_scores[symbol] = (
            exp_r * (0.6 + risk_score)
            - vol * (1.6 - 0.6 * risk_score)
            - dd * (1.1 - 0.5 * risk_score)
            + f_score * (0.15 + 0.10 * risk_score)
        )

    if not raw_scores:
        return {}

    max_score = max(raw_scores.values())
    min_score = min(raw_scores.values())

    # Temperature controls concentration: higher risk => more concentrated weights.
    temperature = 0.6 - (risk_score * 0.4)
    temperature = max(0.1, min(0.6, temperature))

    import math
    exp_scores = {}
    for symbol, score in raw_scores.items():
        exp_scores[symbol] = math.exp((score - max_score) / temperature)

    total = sum(exp_scores.values())
    if total <= 0 or max_score == min_score:
        count = len(symbol_stats) or 1
        equal = round(1.0 / count, 4)
        return {symbol: equal for symbol in symbol_stats.keys()}

    return {symbol: round(score / total, 4) for symbol, score in exp_scores.items()}

def _universe_from_kse100():
    data = _fetch_kse100()
    symbols = []
    for row in data:
        for key in row.keys():
            if key.lower() in ("symbol", "symbol code", "company", "company code", "ticker"):
                symbol = row.get(key)
                if symbol:
                    symbols.append(symbol.strip())
                break
    return sorted(set(symbols))

def _map_to_db_symbol(symbol, available=None):
    if not symbol:
        return symbol
    if available and symbol in available:
        return symbol
    if symbol.endswith(".KA") or symbol.endswith(".PSX"):
        return symbol
    candidate = f"{symbol}.KA"
    if available and candidate in available:
        return candidate
    return candidate

def _official_ticker(symbol):
    if not symbol:
        return symbol
    return symbol.replace(".KA", "").replace(".PSX", "")

def _default_report_payload():
    return {"updated_at": datetime.datetime.now().isoformat(), "reports": []}

def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _split_list_field(value):
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    if "|" in text:
        return [part.strip() for part in text.split("|") if part.strip()]
    if ";" in text:
        return [part.strip() for part in text.split(";") if part.strip()]
    return [text]

def _report_from_csv_row(row):
    symbol_value = row.get("symbol") or row.get("\ufeffsymbol") or ""
    report = {
        "symbol": _to_db_symbol(symbol_value),
        "company_name": (row.get("company_name") or "").strip(),
        "sector": (row.get("sector") or "").strip(),
        "fundamentals": {
            "revenue_growth_pct": _to_float(row.get("revenue_growth_pct"), 0.0),
            "profit_growth_pct": _to_float(row.get("profit_growth_pct"), 0.0),
            "roe_pct": _to_float(row.get("roe_pct"), 0.0),
            "debt_to_equity": _to_float(row.get("debt_to_equity"), 0.0),
            "pe_ratio": _to_float(row.get("pe_ratio"), 0.0),
            "pb_ratio": _to_float(row.get("pb_ratio"), 0.0),
            "gross_margin_pct": _to_float(row.get("gross_margin_pct"), 0.0),
            "net_margin_pct": _to_float(row.get("net_margin_pct"), 0.0),
        },
        "period_end": (row.get("period_end") or "").strip(),
        "source_urls": _split_list_field(row.get("source_urls")),
        "risk_factors": _split_list_field(row.get("risk_factors")),
        "thesis": (row.get("thesis") or "").strip(),
        "target_view": (row.get("target_view") or "HOLD").strip().upper(),
        "confidence_score": round(_clip(_to_float(row.get("confidence_score"), 0.5), 0.0, 1.0), 2),
        "source_notes": (row.get("source_notes") or "").strip(),
        "updated_at": (row.get("updated_at") or "").strip() or datetime.datetime.now().isoformat(),
    }
    return report

def _report_to_csv_row(report):
    fundamentals = report.get("fundamentals") or {}
    return {
        "symbol": report.get("symbol", ""),
        "company_name": report.get("company_name", ""),
        "sector": report.get("sector", ""),
        "revenue_growth_pct": fundamentals.get("revenue_growth_pct", 0.0),
        "profit_growth_pct": fundamentals.get("profit_growth_pct", 0.0),
        "roe_pct": fundamentals.get("roe_pct", 0.0),
        "debt_to_equity": fundamentals.get("debt_to_equity", 0.0),
        "pe_ratio": fundamentals.get("pe_ratio", 0.0),
        "pb_ratio": fundamentals.get("pb_ratio", 0.0),
        "gross_margin_pct": fundamentals.get("gross_margin_pct", 0.0),
        "net_margin_pct": fundamentals.get("net_margin_pct", 0.0),
        "period_end": report.get("period_end", ""),
        "source_urls": "|".join(report.get("source_urls") or []),
        "risk_factors": "|".join(report.get("risk_factors") or []),
        "thesis": report.get("thesis", ""),
        "target_view": (report.get("target_view") or "HOLD").upper(),
        "confidence_score": report.get("confidence_score", 0.5),
        "source_notes": report.get("source_notes", ""),
        "updated_at": report.get("updated_at", ""),
    }

def _load_equity_reports():
    if os.path.exists(REPORTS_CSV_PATH):
        try:
            with open(REPORTS_CSV_PATH, "r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                reports = []
                for row in reader:
                    symbol_value = (row.get("symbol") or row.get("\ufeffsymbol") or "").strip()
                    if not symbol_value:
                        continue
                    report = _report_from_csv_row(row)
                    reports.append(EquityResearchReport.model_validate(report).model_dump())
            return {
                "updated_at": datetime.datetime.now().isoformat(),
                "reports": reports,
            }
        except Exception:
            pass
    if not os.path.exists(REPORTS_PATH):
        return _default_report_payload()
    try:
        with open(REPORTS_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        reports = payload.get("reports", [])
        if isinstance(reports, list):
            return {
                "updated_at": payload.get("updated_at"),
                "reports": reports
            }
    except Exception:
        pass
    return _default_report_payload()

def _save_equity_reports(reports):
    os.makedirs(os.path.dirname(REPORTS_PATH), exist_ok=True)
    payload = {"updated_at": datetime.datetime.now().isoformat(), "reports": reports}
    csv_fields = [
        "symbol",
        "company_name",
        "sector",
        "revenue_growth_pct",
        "profit_growth_pct",
        "roe_pct",
        "debt_to_equity",
        "pe_ratio",
        "pb_ratio",
        "gross_margin_pct",
        "net_margin_pct",
        "period_end",
        "source_urls",
        "risk_factors",
        "thesis",
        "target_view",
        "confidence_score",
        "source_notes",
        "updated_at",
    ]
    with open(REPORTS_CSV_PATH, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for report in reports:
            writer.writerow(_report_to_csv_row(report))
    with open(REPORTS_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return payload

def _to_db_symbol(symbol):
    if not symbol:
        return ""
    symbol = symbol.strip().upper()
    if symbol.endswith(".KA") or symbol.endswith(".PSX"):
        return symbol
    return f"{symbol}.KA"

def _clip(value, low, high):
    return max(low, min(high, value))

def _score_fundamentals(report):
    fundamentals = report.get("fundamentals") or {}
    rev = float(fundamentals.get("revenue_growth_pct", 0.0))
    profit = float(fundamentals.get("profit_growth_pct", 0.0))
    roe = float(fundamentals.get("roe_pct", 0.0))
    debt = float(fundamentals.get("debt_to_equity", 0.0))
    pe = float(fundamentals.get("pe_ratio", 0.0))
    pb = float(fundamentals.get("pb_ratio", 0.0))
    gross_margin = float(fundamentals.get("gross_margin_pct", 0.0))
    net_margin = float(fundamentals.get("net_margin_pct", 0.0))

    score = 0.0
    used_weight = 0.0

    # Growth values can be negative and still valid, so always include them.
    score += _clip(rev / 25.0, -1.0, 1.0) * 0.20
    used_weight += 0.20
    score += _clip(profit / 25.0, -1.0, 1.0) * 0.20
    used_weight += 0.20

    # For other fields, zero generally means "not available" in uploaded research.
    if roe > 0:
        score += _clip((roe - 12.0) / 15.0, -1.0, 1.0) * 0.20
        used_weight += 0.20
    if gross_margin > 0:
        score += _clip((gross_margin - 20.0) / 20.0, -1.0, 1.0) * 0.10
        used_weight += 0.10
    if net_margin > 0:
        score += _clip((net_margin - 8.0) / 12.0, -1.0, 1.0) * 0.10
        used_weight += 0.10
    if debt > 0:
        score -= _clip((debt - 1.0) / 2.0, -1.0, 1.0) * 0.10
        used_weight += 0.10
    if pe > 0:
        score -= _clip((pe - 15.0) / 20.0, -1.0, 1.0) * 0.05
        used_weight += 0.05
    if pb > 0:
        score -= _clip((pb - 2.0) / 3.0, -1.0, 1.0) * 0.05
        used_weight += 0.05

    if used_weight <= 0:
        return 0.0
    normalized = score / used_weight
    return round(_clip(normalized, -1.0, 1.0), 4)

def _reports_by_symbol():
    payload = _load_equity_reports()
    reports = payload.get("reports", [])
    by_symbol = {}
    for item in reports:
        symbol = _to_db_symbol(item.get("symbol", ""))
        if symbol:
            by_symbol[symbol] = item
    return by_symbol, payload.get("updated_at")

def recommend_portfolio(profile: UserProfile):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, price, timestamp FROM stocks_data")
    rows = cursor.fetchall()
    conn.close()

    symbol_stats, returns_map = _portfolio_stats(rows)
    report_map, reports_updated_at = _reports_by_symbol()
    fundamental_scores = {
        symbol: _score_fundamentals(report)
        for symbol, report in report_map.items()
    }
    market_returns = _market_returns(returns_map)
    risk_score = _risk_score(profile)
    weights = _optimize_portfolio(symbol_stats, risk_score, fundamental_scores)

    available = set(symbol_stats.keys())
    report_universe = [symbol for symbol in report_map.keys() if symbol in available]
    kse100_universe = _universe_from_kse100()
    # If research reports exist, prioritize report symbols as the recommendation universe.
    # Fallback to KSE-100 and then full market stats if no report symbols are available.
    if report_universe:
        scoped_stats = {symbol: symbol_stats[symbol] for symbol in report_universe}
        scoped_scores = {
            symbol: fundamental_scores.get(symbol, 0.0)
            for symbol in report_universe
        }
        weights = _optimize_portfolio(scoped_stats, risk_score, scoped_scores)
    elif kse100_universe:
        normalized_stats = {}
        for sym in kse100_universe:
            db_symbol = _map_to_db_symbol(sym, available)
            stats = symbol_stats.get(db_symbol)
            if stats:
                normalized_stats[db_symbol] = stats
        normalized_scores = {
            symbol: fundamental_scores.get(symbol, 0.0)
            for symbol in normalized_stats.keys()
        }
        weights = _optimize_portfolio(
            normalized_stats, risk_score, normalized_scores
        ) if normalized_stats else {}

    recommendations = []
    target_symbols = report_universe or kse100_universe or list(symbol_stats.keys())
    for sym in target_symbols:
        symbol = _map_to_db_symbol(sym, available)
        stats = symbol_stats.get(symbol)
        report = report_map.get(symbol, {})
        fundamental_score = _score_fundamentals(report) if report else 0.0
        target_view = (report.get("target_view") or "").upper() if report else ""
        confidence = float(report.get("confidence_score", 0.0)) if report else 0.0
        thesis = (report.get("thesis") or "") if report else ""
        if not stats:
            recommendations.append({
                "symbol": symbol,
                "official_ticker": _official_ticker(symbol),
                "expected_return_pct": 0.0,
                "volatility_pct": 0.0,
                "var_95_pct": 0.0,
                "beta": 0.0,
                "drawdown_pct": 0.0,
                "fundamental_score": fundamental_score,
                "report_target_view": target_view or None,
                "report_confidence": round(confidence, 2) if report else None,
                "thesis_summary": thesis[:220] if thesis else None,
                "allocation": 0.0,
                "action": "NO DATA",
                "reason": "No historical data available"
            })
            continue
        exp_return = stats["expected_return"]
        vol = stats["volatility"]
        beta = _beta(returns_map.get(symbol, []), market_returns)
        var_95 = exp_return - 1.65 * vol
        recommendations.append({
            "symbol": symbol,
            "official_ticker": _official_ticker(symbol),
            "expected_return_raw": exp_return,
            "volatility_raw": vol,
            "expected_return_pct": round(exp_return * 100, 2),
            "volatility_pct": round(vol * 100, 2),
            "var_95_pct": round(var_95 * 100, 2),
            "beta": round(beta, 2),
            "drawdown_pct": round(stats["drawdown"] * 100, 2),
            "fundamental_score": fundamental_score,
            "report_target_view": target_view or None,
            "report_confidence": round(confidence, 2) if report else None,
            "thesis_summary": thesis[:220] if thesis else None,
            "allocation": weights.get(symbol, 0.0),
            "action": "",
            "reason": ""
        })

    daily_return = sum(
        rec.get("expected_return_raw", 0.0) * rec["allocation"] for rec in recommendations
    )
    daily_vol = sum(
        rec.get("volatility_raw", 0.0) * rec["allocation"] for rec in recommendations
    )
    trading_days = 252
    portfolio_return = daily_return * trading_days * 100
    portfolio_vol = daily_vol * (trading_days ** 0.5) * 100
    risk_free = 5.0
    sharpe = 0.0
    if portfolio_vol > 0:
        sharpe = (portfolio_return - risk_free) / portfolio_vol

    target_vol = 2.0 + risk_score * 6.0
    if portfolio_vol > target_vol:
        rebalance = "Risk is above target. Consider reducing high-volatility holdings."
    else:
        rebalance = "Risk is within target. Monitor and rebalance quarterly."

    # Assign actions based on allocation ranking and risk profile
    sorted_recs = sorted(recommendations, key=lambda r: r["allocation"], reverse=True)
    total_recs = len(sorted_recs)
    buy_cutoff = max(1, int(total_recs * (0.15 if risk_score >= 0.7 else 0.1)))
    hold_cutoff = max(buy_cutoff + 1, int(total_recs * 0.5))
    for idx, rec in enumerate(sorted_recs):
        if rec["allocation"] <= 0:
            rec["action"] = "AVOID"
            rec["reason"] = "Insufficient allocation score"
        elif idx < buy_cutoff:
            rec["action"] = "BUY"
            rec["reason"] = "Top allocation based on risk-return score"
        elif idx < hold_cutoff:
            rec["action"] = "HOLD"
            rec["reason"] = "Mid allocation based on risk-return score"
        else:
            rec["action"] = "AVOID"
            rec["reason"] = "Low allocation based on risk-return score"

        # Allow a high-confidence research view to override the generated action.
        report_view = rec.get("report_target_view")
        report_conf = rec.get("report_confidence") or 0.0
        if report_view in ("BUY", "HOLD", "AVOID") and report_conf >= 0.75:
            rec["action"] = report_view
            rec["reason"] = f"Aligned to research report ({int(report_conf * 100)}% confidence)"
        elif not report_view:
            rec["reason"] = f"{rec['reason']}; no equity research report found"

    return {
        "risk_score": round(risk_score, 2),
        "risk_level": _risk_level(risk_score),
        "expected_return_pct": round(portfolio_return, 2),
        "portfolio_volatility_pct": round(portfolio_vol, 2),
        "sharpe_ratio": round(sharpe, 2),
        "rebalancing_advice": rebalance,
        "reports_updated_at": reports_updated_at,
        "recommendations": recommendations
    }

@app.get("/stocks")
def get_stocks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks_data")
    rows = cursor.fetchall()
    conn.close()
    enriched = []
    for row in rows:
        symbol, price, volume, timestamp = row
        enriched.append({
            "symbol": symbol,
            "official_ticker": _official_ticker(symbol),
            "price": price,
            "volume": volume,
            "timestamp": timestamp
        })
    return {"data": enriched}

@app.post("/recommendation")
def recommendation(profile: UserProfile):
    return recommend_portfolio(profile)

class Feedback(BaseModel):
    rating: int
    comments: str = ""

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class PortfolioSave(BaseModel):
    user_id: int
    profile: dict
    recommendation: dict

class Fundamentals(BaseModel):
    revenue_growth_pct: float = 0.0
    profit_growth_pct: float = 0.0
    roe_pct: float = 0.0
    debt_to_equity: float = 0.0
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    gross_margin_pct: float = 0.0
    net_margin_pct: float = 0.0

class EquityResearchReport(BaseModel):
    symbol: str
    company_name: str = ""
    sector: str = ""
    fundamentals: Fundamentals
    period_end: str = ""
    source_urls: list[str] = []
    risk_factors: list[str] = []
    thesis: str = ""
    target_view: str = "HOLD"
    confidence_score: float = 0.5
    source_notes: str = ""
    updated_at: str = ""

def _hash_password(password, salt):
    return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()

@app.post("/feedback")
def feedback(payload: Feedback):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_feedback (rating, comments, created_at) VALUES (?, ?, ?)",
        (payload.rating, payload.comments, datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return {"status": "saved"}

@app.post("/users/register")
def register_user(payload: UserRegister):
    conn = get_db()
    cursor = conn.cursor()
    salt = secrets.token_hex(8)
    password_hash = _hash_password(payload.password, salt)
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
            (payload.name, payload.email, password_hash, salt, datetime.datetime.now().isoformat())
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return {"error": "Email already exists"}
    conn.close()
    return {"user_id": user_id, "name": payload.name, "email": payload.email}

@app.post("/users/login")
def login_user(payload: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, password_hash, salt FROM users WHERE email = ?", (payload.email,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"error": "Invalid credentials"}
    user_id, name, email, password_hash, salt = row
    if _hash_password(payload.password, salt) != password_hash:
        return {"error": "Invalid credentials"}
    return {"user_id": user_id, "name": name, "email": email}

@app.post("/portfolios/save")
def save_portfolio(payload: PortfolioSave):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO saved_portfolios (user_id, profile_json, recommendation_json, created_at) VALUES (?, ?, ?, ?)",
        (
            payload.user_id,
            json.dumps(payload.profile),
            json.dumps(payload.recommendation),
            datetime.datetime.now().isoformat()
        )
    )
    conn.commit()
    conn.close()
    return {"status": "saved"}

@app.get("/portfolios/{user_id}")
def get_portfolios(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, profile_json, recommendation_json, created_at FROM saved_portfolios WHERE user_id = ?",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    payload = []
    for pid, profile_json, recommendation_json, created_at in rows:
        payload.append({
            "id": pid,
            "profile": json.loads(profile_json),
            "recommendation": json.loads(recommendation_json),
            "created_at": created_at
        })
    return {"data": payload}

@app.post("/market/upload")
def upload_market_data(file: UploadFile = File(...)):
    raw = file.file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        symbol = row.get("symbol")
        price = row.get("price")
        volume = row.get("volume")
        timestamp = row.get("timestamp")
        if not symbol or price is None or volume is None:
            continue
        if not timestamp:
            timestamp = datetime.datetime.now().isoformat()
        try:
            rows.append((symbol, float(price), int(float(volume)), timestamp))
        except ValueError:
            continue
    conn = get_db()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO stocks_data (symbol, price, volume, timestamp) VALUES (?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()
    return {"inserted": len(rows)}


@app.post("/funds/upload")
def upload_funds_data(file: UploadFile = File(...)):
    """Upload CSV of mutual fund NAV history.
    Expected CSV columns: symbol,date,nav (date in YYYY-MM-DD)
    Multiple rows per symbol allowed.
    This will compute simple fund metrics and write funds_cache.json in the data_pipeline folder.
    """
    raw = file.file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(content))
    histories = {}
    for row in reader:
        symbol = (row.get("symbol") or row.get("ticker") or "").strip()
        date = (row.get("date") or row.get("timestamp") or "").strip()
        nav = row.get("nav") or row.get("price") or ""
        if not symbol or not date or not nav:
            continue
        try:
            nav_val = float(nav)
        except Exception:
            continue
        histories.setdefault(symbol, []).append({"date": date, "nav": nav_val})

    # compute metrics
    funds = []
    for sym, hist in histories.items():
        # simple metrics computation (mirrors pipeline.compute_fund_metrics)
        hist_sorted = sorted(hist, key=lambda x: x.get("date"))
        navs = [float(x.get("nav")) for x in hist_sorted if x.get("nav") is not None]
        if len(navs) < 2:
            metrics = {"expected_return": 0.0, "volatility": 0.0, "drawdown": 0.0, "latest_nav": navs[-1] if navs else None}
        else:
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
            metrics = {"expected_return": mean_ret, "volatility": vol, "drawdown": max_dd, "latest_nav": navs[-1]}
        funds.append({
            "symbol": sym,
            "history_length": len(hist),
            "latest_nav": metrics.get("latest_nav"),
            "expected_return": metrics.get("expected_return"),
            "volatility": metrics.get("volatility"),
            "drawdown": metrics.get("drawdown")
        })

    # save to funds_cache.json
    funds_path = os.path.join(os.path.dirname(__file__), "..", "data_pipeline", "funds_cache.json")
    try:
        with open(funds_path, "w", encoding="utf-8") as handle:
            json.dump({"fetched_at": datetime.datetime.now().isoformat(), "funds": funds}, handle)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "inserted_symbols": len(funds)}

@app.get("/models/metrics")
def model_metrics():
    metrics_path = os.path.join(os.path.dirname(__file__), "..", "data_pipeline", "models_metrics.json")
    if not os.path.exists(metrics_path):
        return {"status": "missing", "message": "Run train_models.py to generate metrics."}
    with open(metrics_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data

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

_kse100_cache = {"fetched_at": None, "data": None}
_kse100_cache_ttl = 6 * 60 * 60

def _fetch_kse100():
    now = datetime.datetime.now()
    if _kse100_cache["fetched_at"]:
        age = (now - _kse100_cache["fetched_at"]).total_seconds()
        if age < _kse100_cache_ttl:
            return _kse100_cache["data"]
    url = "https://dps.psx.com.pk/indices/KSE100"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return []
    parser = _KSE100Parser()
    parser.feed(html)
    rows = parser.rows
    if not rows:
        return []
    header = rows[0]
    data_rows = []
    for row in rows[1:]:
        if len(row) < 2:
            continue
        entry = dict(zip(header, row))
        data_rows.append(entry)
    _kse100_cache["fetched_at"] = now
    _kse100_cache["data"] = data_rows
    return data_rows

@app.get("/kse100")
def kse100():
    data = _fetch_kse100()
    return {"data": data, "source": "PSX DPS", "cached_at": _kse100_cache["fetched_at"]}


@app.get("/funds")
def funds():
    # Return cached mutual fund metrics if available
    funds_path = os.path.join(os.path.dirname(__file__), "..", "data_pipeline", "funds_cache.json")
    if not os.path.exists(funds_path):
        return {"status": "missing", "message": "No fund data cached. Run pipeline or set MUTUAL_FUND_API_URL."}
    try:
        with open(funds_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return {"data": payload.get("funds", []), "cached_at": payload.get("fetched_at")}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

@app.get("/equity-reports")
def list_equity_reports():
    payload = _load_equity_reports()
    reports = payload.get("reports", [])
    enriched = []
    for report in reports:
        symbol = _to_db_symbol(report.get("symbol", ""))
        enriched.append({
            **report,
            "symbol": symbol,
            "official_ticker": _official_ticker(symbol),
            "fundamental_score": _score_fundamentals(report)
        })
    return {"updated_at": payload.get("updated_at"), "count": len(enriched), "reports": enriched}

@app.get("/equity-reports/{symbol}")
def get_equity_report(symbol: str):
    target = _to_db_symbol(symbol)
    payload = _load_equity_reports()
    for report in payload.get("reports", []):
        report_symbol = _to_db_symbol(report.get("symbol", ""))
        if report_symbol == target:
            return {
                "updated_at": payload.get("updated_at"),
                "report": {
                    **report,
                    "symbol": report_symbol,
                    "official_ticker": _official_ticker(report_symbol),
                    "fundamental_score": _score_fundamentals(report)
                }
            }
    return {"status": "missing", "message": f"No report found for {target}"}

@app.post("/equity-reports")
def upsert_equity_report(payload: EquityResearchReport):
    body = payload.model_dump()
    body["symbol"] = _to_db_symbol(body.get("symbol", ""))
    if not body["updated_at"]:
        body["updated_at"] = datetime.datetime.now().isoformat()
    body["target_view"] = (body.get("target_view") or "HOLD").upper()
    body["confidence_score"] = round(_clip(float(body.get("confidence_score", 0.5)), 0.0, 1.0), 2)

    existing = _load_equity_reports()
    reports = existing.get("reports", [])
    replaced = False
    for i, report in enumerate(reports):
        if _to_db_symbol(report.get("symbol", "")) == body["symbol"]:
            reports[i] = body
            replaced = True
            break
    if not replaced:
        reports.append(body)
    saved = _save_equity_reports(reports)
    return {
        "status": "ok",
        "updated_at": saved.get("updated_at"),
        "symbol": body["symbol"],
        "fundamental_score": _score_fundamentals(body)
    }

@app.post("/equity-reports/upload")
def upload_equity_reports(file: UploadFile = File(...)):
    raw = file.file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"status": "error", "message": "Only UTF-8 CSV/JSON files are supported."}
    validated = []

    parsed_json = None
    try:
        parsed_json = json.loads(content)
    except Exception:
        parsed_json = None

    if parsed_json is not None:
        if isinstance(parsed_json, dict):
            input_reports = parsed_json.get("reports", [])
        elif isinstance(parsed_json, list):
            input_reports = parsed_json
        else:
            return {"status": "error", "message": "JSON payload must be a report list or {\"reports\": [...]}."}

        for item in input_reports:
            try:
                report = EquityResearchReport.model_validate(item).model_dump()
                report["symbol"] = _to_db_symbol(report.get("symbol", ""))
                report["target_view"] = (report.get("target_view") or "HOLD").upper()
                report["confidence_score"] = round(
                    _clip(float(report.get("confidence_score", 0.5)), 0.0, 1.0), 2
                )
                if not report["updated_at"]:
                    report["updated_at"] = datetime.datetime.now().isoformat()
                validated.append(report)
            except Exception:
                continue
    else:
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            try:
                report = _report_from_csv_row(row)
                report = EquityResearchReport.model_validate(report).model_dump()
                validated.append(report)
            except Exception:
                continue

    if not validated:
        return {"status": "error", "message": "No valid report rows found (CSV or JSON)."}

    existing_payload = _load_equity_reports()
    existing = {
        _to_db_symbol(report.get("symbol", "")): report
        for report in existing_payload.get("reports", [])
    }
    for report in validated:
        existing[report["symbol"]] = report
    saved = _save_equity_reports(list(existing.values()))
    return {
        "status": "ok",
        "updated_at": saved.get("updated_at"),
        "accepted_reports": len(validated),
        "total_reports": len(saved.get("reports", []))
    }

@app.post("/ingest/run")
def run_ingestion():
    pipeline_path = os.path.join(os.path.dirname(__file__), "..", "data_pipeline", "pipeline.py")
    result = subprocess.run(
        [sys.executable, pipeline_path],
        capture_output=True,
        text=True,
        check=False
    )
    return {
        "status": "ok" if result.returncode == 0 else "error",
        "code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip()
    }


@app.post("/funds/refresh")
def refresh_funds():
    pipeline_path = os.path.join(os.path.dirname(__file__), "..", "data_pipeline", "pipeline.py")
    result = subprocess.run(
        [sys.executable, pipeline_path, "--fetch-funds"],
        capture_output=True,
        text=True,
        check=False
    )
    return {
        "status": "ok" if result.returncode == 0 else "error",
        "code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip()
    }

@app.get("/")
def home():
    return {"message": "Investment Agent API Running"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
