"""Part 2: score an existing model on the holdout and record the evidence in MLflow.

Usage: python src/evaluate.py --run-id <id> [--threshold 0.5]
       python src/evaluate.py --version <n>   [--threshold 0.5]

See SPEC.md, Part 2, for what the evaluation run must contain.
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--version")
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()
    raise NotImplementedError("Part 2")


if __name__ == "__main__":
    main()
