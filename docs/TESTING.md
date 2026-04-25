# Testing Checklist (MVP)

## Data Pipeline
- Run `python backend\data_pipeline\pipeline.py`
- Confirm rows appear in `stocks.db`
- Optional: run scheduled mode with `--schedule` to verify loop

## API
- `GET /stocks` returns rows
- `POST /recommendation` returns risk level + allocation + metrics
- `POST /feedback` stores a record
- `POST /users/register` and `POST /users/login` work
- `POST /portfolios/save` then `GET /portfolios/{user_id}`
- `POST /market/upload` accepts CSV and inserts rows
- `POST /ingest/run` triggers pipeline
- `GET /models/metrics` returns metrics after training

## Frontend
- User profile submission returns recommendation
- Save portfolio works after login
- CSV upload works
- Run ingestion button updates status
- Model metrics table loads after training
