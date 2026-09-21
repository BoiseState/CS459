"""
Shared test machinery. GIVEN. The test output tells you everything the tests check.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("PIPELINE_DATA_DIR", REPO / "data")).resolve()
EXAMPLE_GATE = "rows_in_vs_trailing_7d"


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------

class Harness:
    """Collects named checks and prints them the same way for every part."""

    def __init__(self, part: str, title: str):
        self.part, self.title = part, title
        self.results: list[tuple[str, bool, list[str]]] = []
        print(f"\n== {part} · {title}")

    def check(self, name: str, ok: bool, detail: list[str] | str = ()) -> bool:
        lines = [detail] if isinstance(detail, str) else list(detail)
        self.results.append((name, ok, lines))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        for line in lines if not ok else []:
            print(f"        {line}")
        return ok

    def note(self, msg: str) -> None:
        print(f"        {msg}")

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.results)

    def summary_line(self) -> str:
        n_ok = sum(ok for _, ok, _ in self.results)
        return f"{'PASS' if self.passed else 'FAIL'}  {self.part:<7} {self.title:<28} {n_ok}/{len(self.results)} checks"


def finish(h: Harness) -> int:
    print(f"\n{h.summary_line()}")
    return 0 if h.passed else 1


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------

def reset_data(shift: dict[str, float] | None = None, shift_from: date | None = None) -> None:
    """Start from clean data: regenerate events if needed, delete everything the pipeline wrote."""
    from src.generate_events import generate

    wanted = {"shift": shift or {}, "shift_from": str(shift_from) if shift_from else None}
    stamp = DATA / "events" / "_generated.json"
    if not (stamp.exists() and json.loads(stamp.read_text()) == wanted):
        t0 = time.time()
        print(f"  generating events{' with upstream change ' + str(shift) if shift else ''} ...", end="", flush=True)
        generate(DATA, shift, shift_from)
        stamp.write_text(json.dumps(wanted))
        print(f" done ({time.time() - t0:.1f}s)")
    for sub in ("stage", "aggs", "quarantine", "runs", "models"):
        shutil.rmtree(DATA / sub, ignore_errors=True)
    (DATA / "incident.json").unlink(missing_ok=True)


def cli(*args: str) -> tuple[int, str]:
    """Run the pipeline the way a scheduler would: as a separate process, through its command line."""
    env = {**os.environ, "PIPELINE_DATA_DIR": str(DATA)}
    p = subprocess.run([sys.executable, "-m", "src.runner", *args], cwd=REPO, env=env,
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def run_in_process(dt: date, **kw) -> dict:
    """Run one date inside this process (faster for many dates). Returns the manifest."""
    from src.runner import run_date
    with redirect_stdout(io.StringIO()):
        return run_date(dt, DATA, log=lambda *_: None, **kw)


def con_with_views() -> duckdb.DuckDBPyConnection:
    """A connection with the same views `make sql` gives you. Views whose files do not exist yet are skipped."""
    con = duckdb.connect()
    for name, sql in VIEWS.items():
        try:
            con.execute(f"CREATE OR REPLACE VIEW {name} AS {sql}")
        except duckdb.IOException:
            pass
    return con


VIEWS = {
    "runs":       f"SELECT * FROM read_json('{DATA}/runs/*.json', union_by_name = true)",
    "models":     f"SELECT * FROM read_json('{DATA}/models/registry.json')",
    "incident":   f"SELECT * FROM read_json('{DATA}/incident.json')",
    "aggs":       f"SELECT * FROM read_parquet('{DATA}/aggs/*/*.parquet', hive_partitioning = true)",
    "orders":     f"SELECT * FROM read_parquet('{DATA}/events/orders/*/*.parquet', hive_partitioning = true)",
    "deliveries": f"SELECT * FROM read_parquet('{DATA}/events/deliveries/*/*.parquet', hive_partitioning = true)",
}


# ----------------------------------------------------------------------------
# Looking at partitions
# ----------------------------------------------------------------------------

def partition_dir(dt: date | str, table: str = "aggs") -> Path:
    return DATA / table / f"dt={dt}"


def partition_rows(dt: date | str, table: str = "aggs") -> int | None:
    d = partition_dir(dt, table)
    if not list(d.glob("*.parquet")):
        return None
    return duckdb.sql(f"SELECT count(*) FROM read_parquet('{d}/*.parquet')").fetchone()[0]


def partition_hash(dt: date | str, table: str = "aggs") -> str | None:
    """A hash of the partition's content: every row, sorted, ignoring which run wrote it."""
    d = partition_dir(dt, table)
    if not list(d.glob("*.parquet")):
        return None
    cols = [c[0] for c in duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{d}/*.parquet')").fetchall()]
    keep = ", ".join(f'"{c}"' for c in cols if c != "run_id")
    return duckdb.sql(f"""
        SELECT md5(string_agg(row_text, chr(10) ORDER BY row_text))
        FROM (SELECT to_json(t)::VARCHAR AS row_text FROM (SELECT {keep} FROM read_parquet('{d}/*.parquet')) AS t)
    """).fetchone()[0]


def fmt(n: int | None) -> str:
    return "missing" if n is None else f"{n:,} rows"


def short(h: str | None) -> str:
    return "missing" if h is None else h[:8]
