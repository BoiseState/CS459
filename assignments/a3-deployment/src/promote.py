"""Move @champion to the @challenger version, if its gate passed. Provided; not graded.

Usage: python src/promote.py            (refuses if gate.passed is not "true")
"""
from mlflow import MlflowClient

from tracking import MODEL_NAME


def main():
    client = MlflowClient()
    ch = client.get_model_version_by_alias(MODEL_NAME, "challenger")
    if ch.tags.get("gate.passed") != "true":
        raise SystemExit(f"v{ch.version} did not pass the gate: {ch.tags.get('gate.reasons')}")
    old = client.get_model_version_by_alias(MODEL_NAME, "champion")
    client.set_model_version_tag(MODEL_NAME, ch.version, "previous_champion", old.version)
    client.set_registered_model_alias(MODEL_NAME, "champion", ch.version)
    print(f"@champion: v{old.version} -> v{ch.version}")


if __name__ == "__main__":
    main()
