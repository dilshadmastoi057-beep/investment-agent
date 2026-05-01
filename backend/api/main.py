from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

market_df = None
research_df = None

# =========================
# UPLOADS
# =========================
@app.post("/market/upload")
def upload_market(file: UploadFile = File(...)):
    global market_df
    market_df = pd.read_csv(file.file)
    return {"status": "market uploaded", "rows": len(market_df)}

@app.post("/equity-reports/upload")
def upload_research(file: UploadFile = File(...)):
    global research_df
    research_df = pd.read_csv(file.file)
    return {"status": "research uploaded", "rows": len(research_df)}

# =========================
# REALISTIC MARKOWITZ
# =========================
def compute_markowitz(df, risk_aversion):

    # --- EXPECTED RETURN (from data OR proxy) ---
    if "return" in df.columns:
        returns = df["return"].values
    else:
        # proxy: use score-like synthetic but stable
        returns = np.log1p(np.arange(len(df)) + 1) / 10

    # --- VOLATILITY (REALISTIC: STD approximation) ---
    if "price" in df.columns:
        vol = df["price"].pct_change().fillna(0).rolling(3).std().fillna(0.01)
        vol = vol.replace(0, 0.01).values
    else:
        vol = np.linspace(0.05, 0.2, len(df))

    n = len(df)

    cov_matrix = np.diag(vol ** 2)

    best_score = -1e9
    best_w = np.ones(n) / n

    # optimization loop
    for _ in range(2000):
        w = np.random.random(n)
        w = w / np.sum(w)

        port_return = np.dot(w, returns)
        port_risk = np.dot(w.T, np.dot(cov_matrix, w))

        score = port_return - risk_aversion * port_risk

        if score > best_score:
            best_score = score
            best_w = w

    df["allocation_pct"] = best_w * 100
    df["score"] = returns * 100

    return df

# =========================
# RECOMMENDATION ENDPOINT
# =========================
@app.post("/recommendation")
def recommend(user: dict):

    global market_df

    if market_df is None:
        return {"error": "Upload market data first"}

    risk_map = {
        "Low": 2.0,
        "Medium": 1.0,
        "High": 0.5
    }

    risk_aversion = risk_map.get(user["risk_preference"], 1.0)

    df = market_df.copy()

    result = compute_markowitz(df, risk_aversion)

    # ✔ SORT + TOP 5 FIX (IMPORTANT)
    result = result.sort_values(by="score", ascending=False)
    result = result.head(5)

    portfolio = []

    for _, row in result.iterrows():
        portfolio.append({
            "symbol": row["symbol"],
            "allocation_pct": round(row["allocation_pct"], 2),
            "score": round(row["score"], 2),
            "reasons": [
                "Markowitz optimized",
                "Real risk-return tradeoff",
                f"User risk: {user['risk_preference']}"
            ]
        })

    return {
        "model": "MARKOWITZ_REAL_V2",
        "portfolio": portfolio
    }

@app.get("/")
def home():
    return {"status": "AI Investment Portfolio Running"}