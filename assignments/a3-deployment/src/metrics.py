"""Threshold metrics, overall and per group, with the names the spec requires.

Provided in full. Computing these is not the point of the assignment; logging them
where the gate can find them is.
"""
import matplotlib

matplotlib.use("Agg")  # no screen inside the container; draw to files
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import (average_precision_score, confusion_matrix,  # noqa: E402
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)

# name -> (column, value). These names are part of the spec: the gate looks them up.
GROUPS = {
    "hotel.city":            ("hotel", "City Hotel"),
    "hotel.resort":          ("hotel", "Resort Hotel"),
    "segment.online_ta":     ("market_segment", "Online TA"),
    "segment.offline_ta_to": ("market_segment", "Offline TA/TO"),
    "segment.groups":        ("market_segment", "Groups"),
    "segment.direct":        ("market_segment", "Direct"),
    "segment.corporate":     ("market_segment", "Corporate"),
}


def _at_threshold(y, score, threshold):
    flag = score >= threshold
    return {
        "n": float(len(y)),
        "cancel_rate": float(np.mean(y)) if len(y) else float("nan"),
        "flag_rate": float(np.mean(flag)) if len(y) else float("nan"),
        "precision": float(precision_score(y, flag, zero_division=0)),
        "recall": float(recall_score(y, flag, zero_division=0)),
    }


def evaluate(df, score, threshold, prefix):
    """Every metric for one period, as a flat dict ready for mlflow.log_metrics.

    df: the rows that were scored (needs is_canceled, hotel, market_segment).
    score: predicted probability of cancellation, one per row.
    prefix: the period name, e.g. "validation" or "holdout".

    Returns names like "holdout.precision", "holdout.hotel.city.precision".
    """
    y = df["is_canceled"].to_numpy()
    score = np.asarray(score)
    out = {f"{prefix}.roc_auc": float(roc_auc_score(y, score)),
           f"{prefix}.pr_auc": float(average_precision_score(y, score))}
    out.update({f"{prefix}.{k}": v for k, v in _at_threshold(y, score, threshold).items()})
    for name, (col, value) in GROUPS.items():
        mask = (df[col] == value).to_numpy()
        out.update({f"{prefix}.{name}.{k}": v for k, v in _at_threshold(y[mask], score[mask], threshold).items()})
    return out


def pr_curve_figure(df, score, threshold, title=""):
    """Precision against recall across every threshold, with yours marked. Log it with mlflow.log_figure."""
    y, score = df["is_canceled"].to_numpy(), np.asarray(score)
    precision, recall, _ = precision_recall_curve(y, score)
    flag = score >= threshold
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(recall, precision, lw=1.5)
    ax.scatter([recall_score(y, flag, zero_division=0)], [precision_score(y, flag, zero_division=0)],
               color="C3", zorder=3, label=f"your threshold ({threshold:.2f})")
    ax.axhline(0.80, ls="--", lw=1, color="gray", label="precision floor (0.80)")
    ax.set(xlabel="Recall", ylabel="Precision", title=title, xlim=(0, 1), ylim=(0, 1.02))
    ax.legend(loc="lower left")
    fig.tight_layout()
    return fig


def confusion_figure(df, score, threshold, title=""):
    """Counts of flagged and not flagged against what actually happened. Log it with mlflow.log_figure."""
    y = df["is_canceled"].to_numpy()
    cm = confusion_matrix(y, (np.asarray(score) >= threshold).astype(int), labels=[0, 1])
    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    ax.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_xticks([0, 1], ["not flagged", "flagged"])
    ax.set_yticks([0, 1], ["showed up", "canceled"])
    ax.set(xlabel="Model", ylabel="What happened", title=title)
    fig.tight_layout()
    return fig
