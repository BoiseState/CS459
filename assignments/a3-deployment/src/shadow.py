"""Part 4: shadow the challenger on the next quarter before anyone acts on it.

Usage: python src/shadow.py --as-of 2017-04-30

The plumbing is done for you: reading the data, scoring, building the report in the
shape SPEC.md asks for, writing answers/shadow.json, and logging the run. You write the
three functions marked TODO.
"""
import argparse
import json
from pathlib import Path

import mlflow
from mlflow import MlflowClient
from sklearn.metrics import precision_score, recall_score

from features import FEATURES, load, period
from metrics import GROUPS
from tracking import EXPERIMENT, MODEL_NAME

OUT = Path(__file__).resolve().parents[1] / "answers" / "shadow.json"


def load_by_alias(client, alias):
    """TODO. Return (version, model, threshold) for the version `alias` points at.

    Load the model by its alias, not by a version number. The threshold is the
    "threshold" tag on that version, as a float.
    """
    raise NotImplementedError("Part 4: load_by_alias")


def disagreement(df, champion_flags, challenger_flags):
    """TODO. Return (overall_rate, by_group).

    overall_rate: the share of bookings where one model flags and the other doesn't.
    by_group: the same share within each group of metrics.GROUPS, as {group_name: rate}.
    GROUPS maps each name to (column, value), e.g. "hotel.city": ("hotel", "City Hotel").
    """
    raise NotImplementedError("Part 4: disagreement")


def known_by(df, as_of):
    """TODO. Return a boolean array: True for bookings whose outcome you'd know on `as_of`.

    A booking's outcome is final once its arrival date has passed, so these are the
    bookings with an arrival date before `as_of`.
    """
    raise NotImplementedError("Part 4: known_by")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2017-04-30")
    a = ap.parse_args(argv)
    client = MlflowClient()

    champion_version, champion, champion_threshold = load_by_alias(client, "champion")
    challenger_version, challenger, challenger_threshold = load_by_alias(client, "challenger")

    df = period(load(), "next_quarter")
    flags = {"champion": champion.predict_proba(df[FEATURES])[:, 1] >= champion_threshold,
             "challenger": challenger.predict_proba(df[FEATURES])[:, 1] >= challenger_threshold}
    overall, by_group = disagreement(df, flags["champion"], flags["challenger"])
    known = known_by(df, a.as_of)
    y = df["is_canceled"].to_numpy()

    report = {
        "champion_version": str(champion_version),
        "challenger_version": str(challenger_version),
        "as_of": a.as_of,
        "n": int(len(df)),
        "champion_flag_rate": float(flags["champion"].mean()),
        "challenger_flag_rate": float(flags["challenger"].mean()),
        "disagreement_rate": float(overall),
        "disagreement_by_group": {g: float(r) for g, r in by_group.items()},
        "labeled_fraction": float(known.mean()),
        "labeled": {name: {"precision": float(precision_score(y[known], f[known], zero_division=0)),
                           "recall": float(recall_score(y[known], f[known], zero_division=0))}
                    for name, f in flags.items()},
    }
    OUT.write_text(json.dumps(report, indent=2))

    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name="shadow"):
        mlflow.set_tag("a3.part", "4")
        mlflow.log_params({"champion_version": champion_version, "challenger_version": challenger_version,
                           "as_of": a.as_of})
        flat = {k: v for k, v in report.items() if isinstance(v, float)}
        flat.update({f"disagreement.{g}": v for g, v in report["disagreement_by_group"].items()})
        flat.update({f"labeled.{m}.{k}": v for m, d in report["labeled"].items() for k, v in d.items()})
        mlflow.log_metrics(flat)
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()
