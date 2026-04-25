# How This Project Works (FYP Guide)

## Overview
This system is an AI-based investment portfolio recommendation agent. It:
- Collects market data (PSX JSON feed or CSV upload)
- Profiles the user (age, income, risk preference, goals)
- Estimates returns and risk
- Optimizes portfolio weights
- Provides recommendations and rebalancing advice

## Step-by-Step Usage

1. **Run the backend**
```
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8001 --reload
```

2. **Run the frontend**
```
cd frontend\web
npm start
```

3. **Use the dashboard**
- Enter user profile
- Click **Get Recommendation**
- Review risk metrics and allocation
- Optional: register/login and save portfolio
- Optional: upload CSV or run ingestion

## Model Training

Run:
```
python backend\data_pipeline\train_models.py
```
Then click **Load Metrics** in the UI.

## FYP Plan Mapping

- **User Profiling & Risk Analysis**: Profile form + risk scoring in API
- **AI Engine**: Return estimation + ML training script
- **Portfolio Optimization**: Weight allocation based on risk-return
- **Decision Module**: Recommendation actions (BUY/HOLD/AVOID)
- **Feedback Module**: User feedback endpoint stored in DB
- **Security & Ethics**: Local DB only; demo data; no real trading

## Notes
- Live PSX data requires licensing. Current feed is for academic/demo use.
