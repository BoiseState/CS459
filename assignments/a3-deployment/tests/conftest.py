import ast
import os
import sys
from pathlib import Path

import pytest
from mlflow import MlflowClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tracking import EXPERIMENT, MODEL_NAME  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return MlflowClient()


@pytest.fixture(scope="session")
def exp_id(client):
    exp = client.get_experiment_by_name(EXPERIMENT)
    if exp is None:
        pytest.fail("No experiment yet. Run `make bootstrap` first.")
    return exp.experiment_id


def runs_tagged(client, exp_id, part, extra=""):
    q = f"tags.`a3.part` = '{part}'" + (f" and {extra}" if extra else "")
    return client.search_runs([exp_id], q, order_by=["attributes.start_time DESC"])


def latest(client, exp_id, part, extra=""):
    runs = [r for r in runs_tagged(client, exp_id, part, extra) if r.info.status == "FINISHED"]
    if not runs:
        pytest.fail(f"No finished run tagged a3.part={part}" + (f" with {extra}" if extra else ""))
    return runs[0]


def parse(v):
    if v in ("None", "True", "False"):
        return {"None": None, "True": True, "False": False}[v]
    try:
        return ast.literal_eval(v)
    except (ValueError, SyntaxError):
        return v


@pytest.fixture
def restore_aliases(client):
    """Put @champion and @challenger back after a test moves them."""
    saved = dict(client.get_registered_model(MODEL_NAME).aliases)
    yield
    for alias, version in saved.items():
        client.set_registered_model_alias(MODEL_NAME, alias, version)
