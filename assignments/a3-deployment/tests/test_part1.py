"""Part 1: the training run records enough to rebuild the model."""
import mlflow
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from conftest import latest, parse
from features import PERIODS, build_pipeline, fingerprint, load, period
from metrics import GROUPS

REQUIRED = ["model.class", "features", "data.sha256", "data.rows", "data.first_arrival", "data.last_arrival",
            "code.version", "lib.sklearn", "lib.mlflow", "lib.python", "threshold"] + \
           [f"period.{p}" for p in PERIODS]


@pytest.fixture(scope="module")
def run(client, exp_id):
    return latest(client, exp_id, "1")


def test_required_params(run):
    missing = [p for p in REQUIRED if p not in run.data.params]
    assert not missing, f"missing params: {missing}"


def test_model_params_include_seed(run):
    p = run.data.params
    assert p.get("model.class") == "HistGradientBoostingClassifier"
    assert parse(p.get("model.random_state", "None")) is not None, "model.random_state must be logged and not None"


def test_data_fingerprint_matches_file(run):
    assert run.data.params["data.sha256"] == fingerprint()["sha256"]


@pytest.mark.parametrize("prefix", ["validation", "holdout"])
def test_metrics_logged(run, prefix):
    names = [f"{prefix}.{m}" for m in ("roc_auc", "pr_auc", "precision", "recall", "flag_rate")] + \
            [f"{prefix}.{g}.precision" for g in GROUPS]
    missing = [n for n in names if n not in run.data.metrics]
    assert not missing, f"missing metrics: {missing[:5]}..."


PLOTS = [f"plots/{p}_{k}.png" for p in ("validation", "holdout") for k in ("pr_curve", "confusion_matrix")]


def test_plots_logged(client, run):
    have = {a.path for a in client.list_artifacts(run.info.run_id, "plots")}
    missing = [p for p in PLOTS if p not in have]
    assert not missing, f"missing plots: {missing}"


def test_model_has_signature(run):
    info = mlflow.models.get_model_info(f"runs:/{run.info.run_id}/model")
    assert info.signature is not None, "log the model with an input_example so MLflow records its signature"


def test_rebuild_reproduces_metric(run):
    p = run.data.params
    clf = HistGradientBoostingClassifier(**{k[6:]: parse(v) for k, v in p.items()
                                            if k.startswith("model.") and k != "model.class"})
    feats = p["features"].split(",")
    df = load()
    start, end = p["period.train"].split("..")
    train = df[(df.arrival_date >= start) & (df.arrival_date < end)]
    model = build_pipeline(clf, feats).fit(train[feats], train.is_canceled)
    hold = period(df, "holdout")
    auc = roc_auc_score(hold.is_canceled, model.predict_proba(hold[feats])[:, 1])
    assert abs(auc - run.data.metrics["holdout.roc_auc"]) < 1e-4, \
        f"rebuilt from your logged record: {auc:.5f}; logged: {run.data.metrics['holdout.roc_auc']:.5f}"
