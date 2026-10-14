"""Small MLflow helpers shared by every part."""
import mlflow

# scikit-learn's gradient boosting stores tree nodes in a type MLflow's safe format
# refuses to load unless you vouch for it. We trained these models ourselves.
TRUSTED = ["sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor"]
MODEL_NAME = "cancellations"
EXPERIMENT = "hotel-cancellations"


def log_model(model, input_example=None):
    """Log a scikit-learn model to the active run. Use this instead of mlflow.sklearn.log_model.

    Pass input_example (a few rows of the feature DataFrame) and MLflow records the
    model's input schema (its "signature") alongside it.
    """
    return mlflow.sklearn.log_model(model, name="model", input_example=input_example,
                                    skops_trusted_types=TRUSTED)
