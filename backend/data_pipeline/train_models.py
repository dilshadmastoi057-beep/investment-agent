import os
import sqlite3
import json
import datetime

def _load_rows(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, price, timestamp FROM stocks_data ORDER BY symbol, timestamp")
    rows = cursor.fetchall()
    conn.close()
    return rows

def _build_dataset(rows):
    by_symbol = {}
    for symbol, price, timestamp in rows:
        by_symbol.setdefault(symbol, []).append(float(price))
    features = []
    targets = []
    for symbol, prices in by_symbol.items():
        if len(prices) < 6:
            continue
        returns = []
        for i in range(1, len(prices)):
            prev = prices[i - 1]
            cur = prices[i]
            if prev <= 0:
                returns.append(0.0)
            else:
                returns.append(cur / prev - 1)
        for i in range(3, len(returns) - 1):
            features.append([returns[i - 1], returns[i - 2], returns[i - 3]])
            targets.append(returns[i])
    return features, targets

def main():
    db_path = os.path.join(os.path.dirname(__file__), "stocks.db")
    rows = _load_rows(db_path)
    features, targets = _build_dataset(rows)
    if len(features) < 10:
        print("Not enough data to train models.")
        return

    try:
        import numpy as np
        from sklearn.model_selection import train_test_split
        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.neural_network import MLPRegressor
        from sklearn.metrics import mean_absolute_error
    except ImportError:
        print("Install scikit-learn and numpy to train models.")
        return

    X = np.array(features)
    y = np.array(targets)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    models = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=200, random_state=42),
        "neural_network": MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=1000, random_state=42)
    }

    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        results[name] = {"mae": round(float(mae), 6)}

    metrics = {
        "generated_at": datetime.datetime.now().isoformat(),
        "records": len(rows),
        "samples": len(features),
        "results": results
    }
    output_path = os.path.join(os.path.dirname(__file__), "models_metrics.json")
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    print(f"Saved metrics to {output_path}")

if __name__ == "__main__":
    main()
