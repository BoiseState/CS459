"""Data loading, time periods, and the feature pipeline. Shared by every part.

You should not need to change this file. If you think you do, say why in your writeup.
"""
import hashlib
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA = Path(__file__).resolve().parents[1] / "data" / "hotels.csv"
TARGET = "is_canceled"

# Known when the booking is made.
CATEGORICAL = ["hotel", "meal", "country", "market_segment", "distribution_channel",
               "reserved_room_type", "deposit_type", "customer_type", "agent"]
NUMERIC = ["lead_time", "arrival_month", "stays_in_weekend_nights", "stays_in_week_nights",
           "adults", "children", "babies", "is_repeated_guest", "previous_cancellations",
           "previous_bookings_not_canceled", "adr", "required_car_parking_spaces",
           "total_of_special_requests"]
FEATURES = CATEGORICAL + NUMERIC

# Periods are by arrival date. End dates are exclusive.
PERIODS = {
    "train":        ("2015-07-01", "2016-07-01"),
    "validation":   ("2016-07-01", "2017-01-01"),
    "holdout":      ("2017-01-01", "2017-04-01"),
    "next_quarter": ("2017-04-01", "2017-07-01"),
}


def load(path=DATA):
    """Read the bookings and add the derived columns the features use."""
    df = pd.read_csv(path)
    df["arrival_date"] = pd.to_datetime(
        df.arrival_date_year.astype(str) + "-" + df.arrival_date_month + "-"
        + df.arrival_date_day_of_month.astype(str), format="%Y-%B-%d")
    df["arrival_month"] = df.arrival_date.dt.month
    df["children"] = df["children"].fillna(0)
    top_countries = df.country.value_counts().index[:15]
    df["country"] = df.country.where(df.country.isin(top_countries), "OTHER").fillna("OTHER")
    df["agent"] = df.agent.fillna(0).astype(int).astype(str)
    top_agents = df.agent.value_counts().index[:20]
    df["agent"] = df.agent.where(df.agent.isin(top_agents), "other")
    df["booking_id"] = range(len(df))
    return df


def period(df, name):
    """Rows whose arrival date falls in one of the PERIODS."""
    start, end = PERIODS[name]
    return df[(df.arrival_date >= start) & (df.arrival_date < end)]


def fingerprint(path=DATA):
    """Identify exactly which data file this is: content hash, size, and date range."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    df = load(path)
    return {"sha256": digest, "rows": len(df),
            "first_arrival": str(df.arrival_date.min().date()),
            "last_arrival": str(df.arrival_date.max().date())}


def build_pipeline(classifier, features=FEATURES):
    """One-hot encode the categorical features, pass numeric ones through, then classify."""
    cat = [c for c in features if c in CATEGORICAL or c not in NUMERIC]
    num = [c for c in features if c in NUMERIC]
    pre = ColumnTransformer([
        ("categorical", OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse_output=False), cat),
        ("numeric", "passthrough", num),
    ])
    return Pipeline([("features", pre), ("classifier", classifier)])
