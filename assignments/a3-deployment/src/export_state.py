"""Write everything in your MLflow server to submission/mlflow_export.json. Used by `make submit`."""
import json
from pathlib import Path

from mlflow import MlflowClient

from tracking import EXPERIMENT, MODEL_NAME

OUT = Path(__file__).resolve().parents[1] / "submission" / "mlflow_export.json"


def main():
    c = MlflowClient()
    exp = c.get_experiment_by_name(EXPERIMENT)
    runs = c.search_runs([exp.experiment_id], max_results=5000) if exp else []
    out = {"runs": [{"run_id": r.info.run_id, "run_name": r.info.run_name, "start_time": r.info.start_time,
                     "status": r.info.status, "params": r.data.params, "metrics": r.data.metrics,
                     "tags": {k: v for k, v in r.data.tags.items() if not k.startswith("mlflow.log-model")}}
                    for r in runs],
           "versions": [], "aliases": {}}
    try:
        rm = c.get_registered_model(MODEL_NAME)
        out["aliases"] = dict(rm.aliases)
        for mv in c.search_model_versions(f"name='{MODEL_NAME}'"):
            out["versions"].append({"version": mv.version, "run_id": mv.run_id, "source": mv.source,
                                    "tags": dict(mv.tags), "aliases": list(mv.aliases)})
    except Exception as e:
        out["registry_error"] = str(e)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote {OUT} ({len(out['runs'])} runs, {len(out['versions'])} versions)")


if __name__ == "__main__":
    main()
