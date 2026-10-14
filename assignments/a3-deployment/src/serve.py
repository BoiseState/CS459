"""The prediction service the hotels call. Each booking gets a cancellation score and a flag.

Part 5 is about this file. Start from the incident report in SPEC.md, not from here.
"""
from pathlib import Path

import mlflow
import pandas as pd
import yaml

from features import FEATURES

CONFIG = Path(__file__).resolve().parents[1] / "config" / "serve.yaml"


class Service:
    def __init__(self, config_path=CONFIG):
        cfg = yaml.safe_load(Path(config_path).read_text())
        self.model = mlflow.sklearn.load_model(cfg["model_uri"])
        self.threshold = float(cfg["threshold"])

    def predict(self, bookings: pd.DataFrame) -> list:
        score = self.model.predict_proba(bookings[FEATURES])[:, 1]
        return [{"booking_id": int(b), "cancel_probability": float(s), "flag": bool(s >= self.threshold)}
                for b, s in zip(bookings["booking_id"], score)]
