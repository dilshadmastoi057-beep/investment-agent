import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os

MODEL_PATH = "model.pkl"

def train_model(df: pd.DataFrame):

    df = df.copy()

    # features
    X = df[["price", "volume", "fa_score", "confidence"]]

    # synthetic target (temporary but ML-based)
    y = (df["fa_score"] * 0.6) + (df["confidence"] * 0.4)

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=6,
        random_state=42
    )

    model.fit(X, y)

    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


def predict(model, df):
    X = df[["price", "volume", "fa_score", "confidence"]]
    return model.predict(X)