"""Part 5: replay the incident as a drill. Provided; not graded.

Usage: python src/drill.py

1. Release: point @champion at the @challenger version and update config/serve.yaml,
   exactly as the team's deploy runbook does.
2. Score a fixed batch of bookings with the service.
3. Roll back: point @champion at the previous version, the way ops did at 10:14.
4. Score the same batch again, with the running service and with a freshly started one.
5. Put every alias and the config file back the way they were.

Before you fix anything, the drill reproduces the incident. After, it shouldn't.
"""
from pathlib import Path

import mlflow
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

from features import FEATURES, load, period
from serve import Service
from tracking import MODEL_NAME

CONFIG = Path(__file__).resolve().parents[1] / "config" / "serve.yaml"


def summary(label, preds):
    versions = sorted({str(p.get("model_version", "not reported")) for p in preds})
    rate = sum(p["flag"] for p in preds) / len(preds)
    print(f"  {label:<38} version: {', '.join(versions):<14} flagged: {rate:.1%}")
    return rate


def not_yet(why):
    raise SystemExit(f"make drill can't run yet: {why}")


def alias(client, name):
    try:
        return client.get_model_version_by_alias(MODEL_NAME, name)
    except MlflowException:
        return None


def main():
    client = MlflowClient()
    champ = alias(client, "champion")
    if champ is None:
        not_yet("there's no @champion. Run `make bootstrap` first.")
    new = alias(client, "challenger")
    if new is None:
        not_yet("there's no @challenger yet. The drill replays the release of your challenger, "
                "so it needs Part 3 first: `python src/register.py --run-id <your Part 1 run>`.")
    old_v = champ.version if champ.version != new.version else new.tags.get("previous_champion")
    if not old_v:
        not_yet("@champion and @challenger point at the same version (see SPEC.md, Part 5).")
    old = client.get_model_version(MODEL_NAME, old_v)
    if "threshold" not in old.tags:
        not_yet(f"version {old.version} has no `threshold` tag. Part 3 asks you to tag version 1 "
                "with threshold = 0.65.")
    saved_config = CONFIG.read_text()
    batch = period(load(), "next_quarter").sample(2000, random_state=0)
    try:
        print(f"Release: @champion -> v{new.version}, config updated per the runbook")
        client.set_registered_model_alias(MODEL_NAME, "champion", new.version)
        threshold = new.tags.get("threshold") or client.get_run(new.run_id).data.params.get("threshold", "0.5")
        CONFIG.write_text(f"# Written by the deploy runbook on every release.\n"
                          f"model_uri: models:/{MODEL_NAME}/{new.version}\nthreshold: {threshold}\n")
        svc = Service()
        summary("after release", svc.predict(batch))

        print(f"Rollback at 10:14: @champion -> v{old.version}")
        client.set_registered_model_alias(MODEL_NAME, "champion", old.version)
        summary("after rollback, same service", svc.predict(batch))
        summary("after rollback, restarted service", Service().predict(batch))

        old_threshold = float(old.tags["threshold"])
        model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{old.version}")
        expected = (model.predict_proba(batch[FEATURES])[:, 1] >= old_threshold).mean()
        print(f"  {'before the release, v' + old.version + ' flagged':<38} {'':<23} {expected:.1%}")
    finally:
        client.set_registered_model_alias(MODEL_NAME, "champion", champ.version)
        CONFIG.write_text(saved_config)
        print(f"Restored: @champion -> v{champ.version}, config/serve.yaml as before")


if __name__ == "__main__":
    main()
