"""Part 3: the promotion policy, written down.

should_promote() takes two dicts of holdout metrics, using the names produced by
metrics.evaluate(..., prefix="holdout"). It must not talk to MLflow: register.py
fetches the metrics and passes them in. That keeps the policy testable on its own.

The policy is specified exactly in SPEC.md, Part 3. Implement it as written.
"""
from dataclasses import dataclass, field

PRECISION_FLOOR = 0.80          # overall and per hotel, challenger only
MIN_RECALL_GAIN = 0.03          # challenger recall minus champion recall, overall
MAX_SEGMENT_PRECISION_DROP = 0.05
MIN_SEGMENT_SIZE = 500          # segments with fewer holdout bookings are not checked
TOLERANCE = 1e-9                # for comparisons that land exactly on a limit


@dataclass
class Decision:
    promote: bool
    reasons: list = field(default_factory=list)   # why not, one string per failed rule


def should_promote(champion: dict, challenger: dict) -> Decision:
    raise NotImplementedError("Part 3")
