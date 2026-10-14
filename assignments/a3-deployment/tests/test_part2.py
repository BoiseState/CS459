"""Part 2: verdicts on the history, and fair re-evaluations on the holdout."""
from pathlib import Path

import pytest
import yaml

from conftest import ROOT, latest

REASONS = {"ok", "uses_outcome", "post_booking_features", "random_split", "different_eval_period"}
HISTORY = ["hgb-0130", "hgb-0206", "hgb-0213", "hgb-0220", "hgb-0227"]


def test_answers_complete():
    ans = yaml.safe_load((ROOT / "answers" / "part2.yaml").read_text())
    for name in HISTORY:
        entry = ans.get(name) or {}
        assert isinstance(entry.get("comparable"), bool), f"{name}: comparable must be true or false"
        assert entry.get("reason") in REASONS, f"{name}: reason must be one of {sorted(REASONS)}"
        assert (entry["reason"] == "ok") == entry["comparable"], f"{name}: 'ok' and comparable must agree"


def test_champion_evaluated(client, exp_id):
    run = latest(client, exp_id, "2", "tags.evaluates_version = '1'")
    assert "holdout.precision" in run.data.metrics and "holdout.segment.groups.precision" in run.data.metrics
    assert float(run.data.params.get("threshold", "nan")) == 0.65, "evaluate the champion at the threshold it runs at"
    assert "data.sha256" in run.data.params
