# Investment Agent (FYP MVP)

This project is an AI-based investment portfolio recommendation system aligned with the FYP plan. It provides:
- User profiling and risk analysis
- Portfolio optimization and recommendations
- Market data ingestion (CSV + PSX JSON feed)
- Equity research report ingestion (fundamental-analysis first workflow)
- Model training metrics (Linear Regression, Random Forest, MLP)
- Feedback capture and saved portfolios

## Quick Start

1. Backend setup
```
python -m venv venv
venv\Scripts\activate
pip install -r backend\requirements.txt
```

2. Seed / ingest data
```
python backend\data_pipeline\pipeline.py
```

3. Run API
```
uvicorn backend.api.main:app --reload
```

4. Run the Flask portfolio API
```
set ALPHA_VANTAGE_API_KEY=your_key_here
cd backend\flask_portfolio
python app.py
```

5. Frontend
```
cd frontend\web
npm install
set REACT_APP_PORTFOLIO_API_BASE=http://127.0.0.1:5000
npm start
```

## Flask Portfolio Upgrade

This repo now includes a beginner-friendly Flask service in `backend/flask_portfolio/` for a simple US stock portfolio flow.

- `backend/flask_portfolio/app.py`
  Flask app with `GET /portfolio`
- `backend/flask_portfolio/portfolio_service.py`
  Alpha Vantage fetching + closing price parsing + return math
- `backend/flask_portfolio/.env.example`
  Environment variable example for `ALPHA_VANTAGE_API_KEY`

The Flask endpoint fetches the last 30 daily closes for:
- `AAPL`
- `MSFT`
- `GOOGL`

It computes:
- daily returns
- average daily return for each stock
- equal-weight portfolio return

Frontend integration is added in `frontend/web/src/App.js` through:
- `REACT_APP_PORTFOLIO_API_BASE`

Example response shape:
```json
{
  "returns": {
    "AAPL": 0.0012,
    "MSFT": 0.0008,
    "GOOGL": 0.0011
  },
  "stocks": {
    "AAPL": {
      "closing_prices": [201.44, 202.1],
      "daily_returns": [0.0032],
      "average_return": 0.0012
    }
  },
  "portfolio": {
    "weights": {
      "AAPL": 0.3333,
      "MSFT": 0.3333,
      "GOOGL": 0.3333
    },
    "total_return": 0.00103
  }
}
```

## Main Features

- **User profiling**: age, income, investment amount, risk preference, time horizon, goals
- **Risk metrics**: volatility, beta, drawdown, VaR (approx)
- **Portfolio**: allocation weights with rebalancing advice
- **Equity research**: structured report store (fundamentals, risks, thesis, target view, confidence)
- **Feedback**: user ratings stored in SQLite
- **Market data**:
  - CSV upload via API
  - PSX JSON feed via Pocket Portfolio (no API key)

## Data Ingestion

One-off ingestion:
```
python backend\data_pipeline\pipeline.py
```

Scheduled ingestion (daily):
```
python backend\data_pipeline\pipeline.py --schedule
```

API-triggered ingestion:
```
POST http://127.0.0.1:8000/ingest/run
```

## Model Training

Run training and generate metrics:
```
python backend\data_pipeline\train_models.py
```

Fetch metrics:
```
GET http://127.0.0.1:8000/models/metrics
```

## Key API Endpoints

- `GET /stocks`
- `POST /recommendation`
- `POST /feedback`
- `POST /users/register`
- `POST /users/login`
- `POST /portfolios/save`
- `GET /portfolios/{user_id}`
- `POST /market/upload`
- `POST /ingest/run`
- `GET /equity-reports`
- `GET /equity-reports/{symbol}`
- `POST /equity-reports`
- `POST /equity-reports/upload`

## Equity Research Workflow (No Paid API)

**Sample Data Added**: `backend/data_pipeline/equity_reports_sample.csv` (5 KSE-100 companies for viva/meetings).

1. Copy sample → `equity_reports.csv` or upload:
```
curl -F file=@equity_reports_sample.csv http://127.0.0.1:8002/equity-reports/upload
```
2. Schema: symbol,company_name,sector,... (CSV/JSON supported).
3. API blends fundamentals into scores (P/E penalty, ROE boost).
4. View: `GET /equity-reports` | Test in dashboard recs.

**Supervisor Note**: Viva-ready reports (ABL/HBL/MCB/LUCK/OGDC).

## Notes

- The PSX JSON feed is **unofficial** and intended for academic use.
- For commercial use, obtain licensed PSX data from authorized vendors.
