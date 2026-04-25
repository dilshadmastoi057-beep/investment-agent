# AI Investment Portfolio Recommender (FYP Project)

## Project Overview
**Investment Agent** is an AI-driven system for personalized KSE-100 stock recommendations. Users input profile (age, income, risk tolerance); system outputs optimized portfolio with BUY/HOLD/AVOID actions, backed by quantitative + fundamental analysis.

**Status**: Fully runnable MVP. Backend API (FastAPI/SQLite), React dashboard, PSX data pipeline.

## Key Features
1. **Risk Profiling**: Multi-factor Risk Score = 0.45×Preference + 0.20×Age + 0.20×Time + 0.10×Income + Goals.
2. **Portfolio Optimization** (Modern Portfolio Theory):
   - Stock Score = (Return × wR) - (Vol × wV) - (Drawdown × wD) + Fundamentals.
   - Weights: Softmax with temperature scaling (High Risk = concentrated).
3. **Metrics**: Expected Return, Volatility, Sharpe Ratio (>1.0 excellent), VaR 95%, Beta.
4. **Data**: PSX JSON/CSV + Equity Research (5 sample reports added for viva).
5. **Fundamental Integration**: P/E, ROE, Debt/Equity from uploaded CSVs → boosts scores.

## Architecture
```
Frontend (React): localhost:3000 ← POST /recommendation → Backend (FastAPI:8002)
                                                ↓
Market Data (stocks.db) + Reports (equity_reports.csv/json) ← Pipeline.py
```

## Sample Output (Medium Risk Profile)
```
Risk: Medium (Score: 0.62)
Return: 31.4% | Vol: 2.6% | Sharpe: 10.15 ✓
Top: HBL 33% BUY | ABL 32% BUY | MCB 30% HOLD
```

## Supervisor Enhancements
- **Added**: `equity_reports_sample.csv` (ABL, MCB, HBL, LUCK, OGDC meeting reports).
- **Upload**: POST /equity-reports/upload → Auto-blends into recs.
- **Test**: Run pipeline → Dashboard → See fundamental scores/actions.

## Run Instructions
```
1. pip install -r backend/requirements.txt
2. python backend/data_pipeline/pipeline.py
3. uvicorn backend.api.main:app --port 8002 --reload
4. cd frontend/web && npm start
5. Upload sample CSV → http://localhost:3000
```

**Print Instructions**: File → Print → Scale to fit 1 page. Portrait, no margins.

**Prepared by**: [Your Name] | Date: [Today] | For: Sir Aj

