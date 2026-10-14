"""Part 4: the shadow report matches a rescore."""
import json

import mlflow
import numpy as np
import pytest

from conftest import ROOT, latest
from features import FEATURES, load, period
from tracking import MODEL_NAME

FIELDS = ["champion_version", "challenger_version", "as_of", "n", "champion_flag_rate", "challenger_flag_rate",
          "disagreement_rate", "disagreement_by_group", "labeled_fraction", "labeled"]


@pytest.fixture(scope="module")
def report():
    path = ROOT / "answers" / "shadow.json"
    assert path.exists(), "run src/shadow.py first"
    return json.loads(path.read_text())


def test_fields(report):
    assert not [f for f in FIELDS if f not in report]
    assert set(report["labeled"]) == {"champion", "challenger"}


def test_logged_as_run(client, exp_id):
    latest(client, exp_id, "4")


def test_rescore_matches(client, report):
    df = period(load(), "next_quarter")
    flags = []
    for key in ("champion_version", "challenger_version"):
        v = client.get_model_version(MODEL_NAME, report[key])
        model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{v.version}")
        flags.append(model.predict_proba(df[FEATURES])[:, 1] >= float(v.tags["threshold"]))
    assert abs(np.mean(flags[0] != flags[1]) - report["disagreement_rate"]) < 1e-9
    assert abs(np.mean(df.arrival_date < report["as_of"]) - report["labeled_fraction"]) < 1e-9
