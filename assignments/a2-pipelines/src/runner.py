"""
The pipeline runner. GIVEN. Read the top half; you do not need the bottom half.

What it does, in one sentence: it runs the stages in src/build_features.py in
order, for one date (or a range of dates), writing each stage's output to disk,
checking the gates in src/gates.py between stages 2 and 3, and recording what
happened in a run manifest.

    python -m src.runner --date 2026-03-03
    python -m src.runner --backfill 2026-03-01 2026-03-21
    python -m src.runner --date 2026-03-03 --resume       # skip stages that already finished
    python -m src.runner --date 2026-03-03 --force        # rebuild this date's intermediates from scratch
    python -m src.runner --date 2026-03-03 --retries 1    # retry a failed stage fewer times

Layout under data/ (one partition per date, everywhere):

    data/events/{orders,deliveries}/dt=D/    raw input events (from generate_events)
    data/stage/<stage>/D/                    each stage's output, plus a _SUCCESS marker
    data/aggs/dt=D/                          the published feature table
    data/quarantine/dt=D/                    where a quarantined partition goes instead
    data/runs/<run_id>.json                  one manifest per run

The interface between the runner and a stage is the `Context` object below.
A stage is any function decorated with @stage in build_features.py; it receives a
Context and writes files into `ctx.stage_dir`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb

DEFAULT_RETRIES = 3


# ----------------------------------------------------------------------------
# What a stage sees
# ----------------------------------------------------------------------------

@dataclass
class Context:
    """Everything a stage needs. One Context per (run, date)."""

    dt: date                    # the date this run is building
    run_id: str                 # unique per run; stamp it on what you write
    data_dir: Path              # the data root
    con: duckdb.DuckDBPyConnection
    stage_name: str = ""        # set by the runner before each stage
    aggs_dir: Path | None = None  # where stage 4 publishes: data/aggs, or data/quarantine
    inputs_read: list[str] = field(default_factory=list)

    @property
    def stage_dir(self) -> Path:
        """This stage's output directory for this date. Created before the stage runs."""
        # Not "dt=D": DuckDB treats any "key=value" folder as a hive partition and would
        # override the dt column inside the files with the folder name.
        return self.data_dir / "stage" / self.stage_name / str(self.dt)

    def output_of(self, stage_name: str) -> Path:
        """The output directory of an earlier stage, for this date."""
        return self.data_dir / "stage" / stage_name / str(self.dt)

    def events(self, table: str, start: date, end: date) -> str:
        """A SQL expression that reads raw events for a date range, and records that read."""
        self.inputs_read.append(f"events/{table}/dt={start}..{end}")
        return (f"(SELECT * FROM read_parquet('{self.data_dir}/events/{table}/*/*.parquet', hive_partitioning = true) "
                f"WHERE dt BETWEEN DATE '{start}' AND DATE '{end}')")


@dataclass
class Stage:
    name: str
    fn: object
    after: str | None      # the stage this one depends on


@dataclass
class GateResult:
    """What a gate returns. `passed` is the decision; the rest is for the manifest."""
    passed: bool
    observed: object = None
    expected: object = None
    detail: str = ""


@dataclass
class Gate:
    name: str
    fn: object
    on_fail: str | None     # "fail", "warn", "quarantine", or None (not decided)


class GateFailed(Exception):
    pass


# Registries. build_features.py and gates.py fill these at import time.
STAGES: list[Stage] = []
GATES: list[Gate] = []


def stage(name: str, after: str | None = None):
    """Register a pipeline stage. Stages run in dependency order."""
    def register(fn):
        STAGES.append(Stage(name=name, fn=fn, after=after))
        return fn
    return register


def gate(name: str, on_fail: str | None = None):
    """Register a data gate. Gates run on stage 2's output, before stage 3."""
    if on_fail not in (None, "fail", "warn", "quarantine"):
        raise ValueError(f"gate {name!r}: on_fail must be 'fail', 'warn', 'quarantine' or None, not {on_fail!r}")

    def register(fn):
        GATES.append(Gate(name=name, fn=fn, on_fail=on_fail))
        return fn
    return register


# ----------------------------------------------------------------------------
# Running one date
# ----------------------------------------------------------------------------

def run_date(dt: date, data_dir: Path, *, resume: bool = False, force: bool = False,
             retries: int = DEFAULT_RETRIES, mode: str = "date", log=print) -> dict:
    """Run every stage for one date. Returns the manifest (also written to data/runs/)."""
    import src.build_features  # noqa: F401  (registers the stages)
    import src.gates           # noqa: F401  (registers the gates)

    started = time.time()
    run_id = os.environ.get("PIPELINE_RUN_ID") or f"{utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')}-{secrets.token_hex(2)}"
    manifest = {
        "run_id": run_id,
        "dt": str(dt),
        "mode": mode,
        "git_sha": git_sha(),
        "lockfile_hash": lockfile_hash(),
        "started_at": utcnow().isoformat(timespec="seconds"),
        "finished_at": None,
        "duration_s": None,
        "status": "running",
        "inputs_read": [],
        "outputs_written": [],
        "rows_in": None,
        "rows_out": None,
        "checks": [],
        "stages": [],
        "error": None,
    }
    log(f"run {run_id}  dt={dt}")

    con = duckdb.connect()
    ctx = Context(dt=dt, run_id=run_id, data_dir=data_dir, con=con, aggs_dir=data_dir / "aggs")

    if force:
        for s in STAGES:
            ctx.stage_name = s.name
            shutil.rmtree(ctx.stage_dir, ignore_errors=True)

    try:
        for s in ordered(STAGES):
            ctx.stage_name = s.name
            ctx.stage_dir.mkdir(parents=True, exist_ok=True)

            if resume and (ctx.stage_dir / "_SUCCESS").exists():
                log(f"  stage {s.name:<16} skipped (already finished)")
                manifest["stages"].append({"name": s.name, "status": "skipped", "attempts": 0, "duration_s": 0.0})
                continue

            record = run_stage(s, ctx, retries, log)
            manifest["stages"].append(record)

            # The gates run on stage 2's output, before anything is aggregated or written.
            if s.name == "join_deliveries":
                run_gates(ctx, manifest, log)

        manifest["inputs_read"] = sorted(set(ctx.inputs_read))
        manifest["rows_in"] = count_rows(con, ctx.output_of("read_events"))
        manifest["rows_out"] = count_rows(con, ctx.aggs_dir / f"dt={dt}")
        published = ctx.aggs_dir.relative_to(data_dir) / f"dt={dt}"
        manifest["outputs_written"] = [str(published)]
        manifest["status"] = "quarantined" if ctx.aggs_dir.name == "quarantine" else "success"

    except GateFailed as e:
        manifest["status"] = "failed"
        manifest["error"] = f"gate failed: {e}"
    except Exception as e:  # a stage raised after every retry
        manifest["status"] = "failed"
        manifest["error"] = f"{type(e).__name__}: {e}"
        log(traceback.format_exc().rstrip())
    finally:
        manifest["finished_at"] = utcnow().isoformat(timespec="seconds")
        manifest["duration_s"] = round(time.time() - started, 2)
        write_manifest(data_dir, manifest)
        con.close()

    log(f"  {manifest['status']}  rows_in={manifest['rows_in']}  rows_out={manifest['rows_out']}  "
        f"({manifest['duration_s']}s)  manifest: runs/{run_id}.json")
    return manifest


def run_stage(s: Stage, ctx: Context, retries: int, log) -> dict:
    """Run one stage, retrying on failure. This is the retry loop the writeup asks about."""
    t0 = time.time()
    for attempt in range(1, retries + 1):
        try:
            s.fn(ctx)
            (ctx.stage_dir / "_SUCCESS").write_text(json.dumps({"run_id": ctx.run_id, "finished_at": utcnow().isoformat()}))
            log(f"  stage {s.name:<16} ok ({time.time() - t0:.2f}s)")
            return {"name": s.name, "status": "success", "attempts": attempt, "duration_s": round(time.time() - t0, 2)}
        except Exception as e:
            log(f"  stage {s.name:<16} attempt {attempt} of {retries} failed: {type(e).__name__}: {e}")
            if attempt == retries:
                raise
    raise AssertionError("unreachable")


def run_gates(ctx: Context, manifest: dict, log) -> None:
    """Run every registered gate on this date's joined deliveries, then apply each gate's on_fail."""
    joined = ctx.output_of("join_deliveries") / "joined.parquet"
    ctx.con.execute(f"CREATE OR REPLACE VIEW joined AS SELECT * FROM read_parquet('{joined}')")

    failed_hard: list[str] = []
    for g in GATES:
        try:
            result: GateResult = g.fn(ctx, "joined")
        except Exception as e:
            raise RuntimeError(f"gate {g.name!r} raised {type(e).__name__}: {e}") from e

        behaviour = g.on_fail or "undecided (treated as warn)"
        record = {"gate": g.name, "status": "pass" if result.passed else "fail", "on_fail": behaviour,
                  "observed": result.observed, "expected": result.expected, "detail": result.detail}
        manifest["checks"].append(record)
        log(f"  gate  {g.name:<24} {record['status']}  observed={result.observed}  expected={result.expected}")

        if not result.passed:
            if g.on_fail == "fail":
                failed_hard.append(g.name)
            elif g.on_fail == "quarantine":
                ctx.aggs_dir = ctx.data_dir / "quarantine"
                log(f"        -> on_fail=quarantine: this date will be written to quarantine/, not aggs/")
            else:
                log(f"        -> on_fail={behaviour}: continuing")

    if failed_hard:
        raise GateFailed(", ".join(failed_hard))


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

def ordered(stages: list[Stage]) -> list[Stage]:
    """Topological order: a stage runs after the stage it names in `after`."""
    done, out = set(), []
    remaining = list(stages)
    while remaining:
        progress = False
        for s in list(remaining):
            if s.after is None or s.after in done:
                out.append(s); done.add(s.name); remaining.remove(s); progress = True
        if not progress:
            raise RuntimeError("stage dependency cycle or unknown `after`: " + ", ".join(s.name for s in remaining))
    return out


def count_rows(con, partition_dir: Path) -> int | None:
    files = sorted(partition_dir.glob("*.parquet")) if partition_dir.exists() else []
    if not files:
        return None
    return sum(con.execute(f"SELECT count(*) FROM read_parquet('{f}')").fetchone()[0] for f in files)


def write_manifest(data_dir: Path, manifest: dict) -> None:
    runs = data_dir / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{manifest['run_id']}.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")


def utcnow() -> datetime:
    fixed = os.environ.get("PIPELINE_NOW")   # tests and fixtures pin the clock
    return datetime.fromisoformat(fixed) if fixed else datetime.now(timezone.utc)


def git_sha() -> str:
    if os.environ.get("PIPELINE_GIT_SHA"):
        return os.environ["PIPELINE_GIT_SHA"]
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              timeout=5, cwd=Path(__file__).resolve().parent.parent).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def lockfile_hash() -> str:
    lock = Path(__file__).resolve().parent.parent / "uv.lock"
    return "sha256:" + hashlib.sha256(lock.read_bytes()).hexdigest()[:12] if lock.exists() else "none"


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# ----------------------------------------------------------------------------
# Command line
# ----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run the feature pipeline for one date or a range of dates.")
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument("--date", type=date.fromisoformat, metavar="YYYY-MM-DD")
    which.add_argument("--backfill", nargs=2, type=date.fromisoformat, metavar=("START", "END"))
    p.add_argument("--resume", action="store_true", help="skip stages whose _SUCCESS marker exists for the date")
    p.add_argument("--force", action="store_true", help="delete the date's stage intermediates first")
    p.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help=f"attempts per stage (default {DEFAULT_RETRIES})")
    p.add_argument("--data-dir", type=Path, default=Path(os.environ.get("PIPELINE_DATA_DIR", "data")))
    a = p.parse_args(argv)

    if a.date:
        dates, mode = [a.date], "date"
    else:
        if a.backfill[1] < a.backfill[0]:
            p.error("--backfill END is before START")
        dates, mode = list(daterange(*a.backfill)), "backfill"
        print(f"backfill {a.backfill[0]} to {a.backfill[1]}: {len(dates)} dates")

    for i, dt in enumerate(dates, 1):
        m = run_date(dt, a.data_dir, resume=a.resume, force=a.force, retries=a.retries, mode=mode)
        if m["status"] == "failed":
            if len(dates) > 1:
                print(f"backfill stopped at {dt} ({i - 1} of {len(dates)} dates completed)")
            return 1
    return 0


if __name__ == "__main__":
    # Run through the imported module, not this __main__ copy, so that the stages and
    # gates registered by build_features.py and gates.py land in the same registries.
    from src.runner import main as _main
    sys.exit(_main())
