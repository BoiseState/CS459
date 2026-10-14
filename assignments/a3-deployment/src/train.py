"""Train a cancellation model and record it in MLflow.

Usage (inside the container): python src/train.py

PART 1: this works, and it logs almost nothing. See SPEC.md, Part 1.
"""
import mlflow
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from features import FEATURES, build_pipeline, load, period
from tracking import EXPERIMENT


def main():
    mlflow.set_experiment(EXPERIMENT)
    df = load()
    train, holdout = period(df, "train"), period(df, "holdout")

    model = build_pipeline(HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05))
    model.fit(train[FEATURES], train.is_canceled)
    score = model.predict_proba(holdout[FEATURES])[:, 1]

    with mlflow.start_run(run_name="hgb"):
        mlflow.log_metric("auc", roc_auc_score(holdout.is_canceled, score))


if __name__ == "__main__":
    main()
