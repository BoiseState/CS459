"""`make doctor`: check the environment. If you email me about setup, send this output."""
import platform
import sys
import urllib.request

ok = True


def check(name, fn):
    global ok
    try:
        detail = fn()
        print(f"  ok    {name}" + (f": {detail}" if detail else ""))
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  FAIL  {name}: {e}")


print(f"python {platform.python_version()} on {platform.machine()}")
check("packages", lambda: __import__("mlflow").__version__ + ", sklearn " + __import__("sklearn").__version__)
check("data file", lambda: (lambda f: f"{f['rows']} bookings, sha256 {f['sha256'][:12]}")(__import__("features").fingerprint()))


def server():
    import mlflow
    uri = mlflow.get_tracking_uri()
    urllib.request.urlopen(uri.rstrip("/") + "/health", timeout=5)
    return uri


check("MLflow server", server)


def history():
    from mlflow import MlflowClient
    from tracking import EXPERIMENT, MODEL_NAME
    c = MlflowClient()
    if c.get_experiment_by_name(EXPERIMENT) is None:
        return "not bootstrapped yet (run make bootstrap)"
    return "champion is v" + c.get_model_version_by_alias(MODEL_NAME, "champion").version


check("history", history)
print("all checks passed" if ok else "some checks FAILED")
sys.exit(0 if ok else 1)
