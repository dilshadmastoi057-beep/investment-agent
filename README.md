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

4. Frontend
```
cd frontend\web
npm install
npm start
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
