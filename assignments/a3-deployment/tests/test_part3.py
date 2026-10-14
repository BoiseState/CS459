"""Part 3: the gate, and what register.py leaves in the registry."""
import pytest

from conftest import latest
from gate import should_promote
from tracking import MODEL_NAME


def metrics(precision=0.85, city=0.85, resort=0.85, recall=0.60, seg_precision=0.90, seg_n=1000):
    m = {"holdout.precision": precision, "holdout.recall": recall,
         "holdout.hotel.city.precision": city, "holdout.hotel.resort.precision": resort}
    for s in ["online_ta", "offline_ta_to", "groups", "direct", "corporate"]:
        m[f"holdout.segment.{s}.precision"] = seg_precision
        m[f"holdout.segment.{s}.n"] = seg_n
    return m


def test_clear_pass():
    assert should_promote(metrics(recall=0.50), metrics(recall=0.60)).promote


def test_below_floor_fails():
    d = should_promote(metrics(recall=0.50), metrics(recall=0.60, resort=0.79))
    assert not d.promote and d.reasons


def test_not_enough_recall_gain_fails():
    assert not should_promote(metrics(recall=0.58), metrics(recall=0.60)).promote


def test_missing_metric_fails_closed():
    ch = metrics(recall=0.60)
    del ch["holdout.hotel.city.precision"]
    assert not should_promote(metrics(recall=0.50), ch).promote


def test_champion_threshold_tagged(client):
    assert client.get_model_version(MODEL_NAME, "1").tags.get("threshold") == "0.65"


def test_challenger_registered_and_gated(client, exp_id):
    v = client.get_model_version_by_alias(MODEL_NAME, "challenger")
    assert v.version != "1"
    for tag in ("threshold", "gate.passed", "gate.reasons"):
        assert tag in v.tags, f"challenger v{v.version} is missing tag {tag}"
    assert v.tags["gate.passed"] in ("true", "false")
    source = client.get_run(v.run_id)
    assert source.data.params.get("threshold") == v.tags["threshold"]
    champ = latest(client, exp_id, "2", "tags.evaluates_version = '1'")
    hold = lambda r: {k: x for k, x in r.data.metrics.items() if k.startswith("holdout.")}
    expected = should_promote(hold(champ), hold(source)).promote
    assert v.tags["gate.passed"] == str(expected).lower(), "gate.passed doesn't match your own gate on the logged metrics"
