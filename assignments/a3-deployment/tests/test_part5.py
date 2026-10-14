"""Part 5: after a rollback, the service behaves like the old model again, and says which model answered."""
import mlflow
import pytest

from features import FEATURES, load, period
from serve import Service
from tracking import MODEL_NAME


@pytest.fixture(scope="module")
def batch():
    return period(load(), "next_quarter").sample(300, random_state=1)


@pytest.fixture
def versions(client):
    champ = client.get_model_version_by_alias(MODEL_NAME, "champion").version
    new = client.get_model_version_by_alias(MODEL_NAME, "challenger").version
    old = champ if champ != new else client.get_model_version(MODEL_NAME, new).tags.get("previous_champion")
    assert old and old != new, "need @champion and @challenger on different versions"
    return old, new


def test_reports_version(client, batch):
    champ = client.get_model_version_by_alias(MODEL_NAME, "champion").version
    preds = Service().predict(batch)
    assert {str(p.get("model_version")) for p in preds} == {champ}


def test_rollback_restores_old_behavior(client, batch, versions, restore_aliases):
    old, new = versions
    client.set_registered_model_alias(MODEL_NAME, "champion", new)
    svc = Service()
    svc.predict(batch)
    client.set_registered_model_alias(MODEL_NAME, "champion", old)
    got = [p["flag"] for p in svc.predict(batch)]
    v = client.get_model_version(MODEL_NAME, old)
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{old}")
    want = list(model.predict_proba(batch[FEATURES])[:, 1] >= float(v.tags["threshold"]))
    assert got == want, f"after rolling back to v{old}, {sum(g != w for g, w in zip(got, want))} of {len(want)} flags differ from v{old}'s own behavior"
