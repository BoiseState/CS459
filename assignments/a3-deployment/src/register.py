"""Part 3: register a challenger, gate it against the champion, and record the result.

Usage: python src/register.py --run-id <the training run you want to promote>

What this must do is in SPEC.md, Part 3. In short:
  1. Register the run's model as a new version of the registered model.
  2. Put the run's threshold on the new version as a tag named "threshold".
  3. Find the champion's evaluation run (from Part 2) and read its holdout metrics.
  4. Read the challenger's holdout metrics from its training run.
  5. Call gate.should_promote(champion_metrics, challenger_metrics).
  6. Tag the new version: gate.passed ("true" or "false") and gate.reasons.
  7. Point the @challenger alias at the new version. Do not move @champion here.
"""
import argparse

from mlflow import MlflowClient

from gate import should_promote
from tracking import MODEL_NAME


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    client = MlflowClient()
    raise NotImplementedError("Part 3")


if __name__ == "__main__":
    main()
