"""Part 0 · the happy path. One date, end to end, on clean data. This one passes before you change anything."""

import json
import sys

from tests.common import DATA, Harness, cli, finish, fmt, partition_rows, reset_data


def run() -> Harness:
    h = Harness("part 0", "happy path")
    reset_data()

    rc, out = cli("--date", "2026-03-03")
    h.check("the pipeline runs one date and exits 0", rc == 0, out.strip().splitlines()[-12:])

    rows = partition_rows("2026-03-03")
    h.check("aggs/dt=2026-03-03 exists and has rows", bool(rows), f"aggs/dt=2026-03-03: {fmt(rows)}")

    manifests = sorted((DATA / "runs").glob("*.json")) if (DATA / "runs").exists() else []
    ok = False
    if manifests:
        m = json.loads(manifests[-1].read_text())
        ok = m.get("status") == "success" and m.get("outputs_written") == ["aggs/dt=2026-03-03"]
    h.check("a run manifest was written and says success", ok,
            [f"{len(manifests)} manifest(s) in data/runs/"] + ([json.dumps(m, indent=2)[:600]] if manifests else []))
    if ok:
        h.note(f"manifest: data/runs/{manifests[-1].name}  rows_in={m['rows_in']:,}  rows_out={m['rows_out']:,}")
    return h


if __name__ == "__main__":
    sys.exit(finish(run()))
