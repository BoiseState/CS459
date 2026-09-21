"""Part 1 · it ran twice. The same date twice, then a two-week backfill twice. Nothing may change."""

import sys
from datetime import date, timedelta

from tests.common import Harness, cli, finish, fmt, partition_hash, partition_rows, reset_data, short

DATE = "2026-03-03"
BACKFILL = ("2026-03-01", "2026-03-14")


def run() -> Harness:
    h = Harness("part 1", "it ran twice")
    reset_data()

    # Check A: the same date, twice.
    cli("--date", DATE)
    rows1, hash1 = partition_rows(DATE), partition_hash(DATE)
    cli("--date", DATE)
    rows2, hash2 = partition_rows(DATE), partition_hash(DATE)

    h.check("running the same date twice leaves the partition unchanged",
            rows1 is not None and rows1 == rows2 and hash1 == hash2, [
                f"aggs/dt={DATE}  after 1 run : {fmt(rows1):>12}  hash {short(hash1)}",
                f"aggs/dt={DATE}  after 2 runs: {fmt(rows2):>12}  hash {short(hash2)}",
                "A pipeline you cannot safely re-run is a pipeline you cannot operate.",
            ])

    # Check B: a backfill over two weeks, twice. Every date must survive both passes.
    start, end = date.fromisoformat(BACKFILL[0]), date.fromisoformat(BACKFILL[1])
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    rc1, out1 = cli("--backfill", *BACKFILL)
    first = {d: (partition_rows(d), partition_hash(d)) for d in dates}
    rc2, out2 = cli("--backfill", *BACKFILL)
    second = {d: (partition_rows(d), partition_hash(d)) for d in dates}

    missing = [str(d) for d in dates if first[d][0] is None]
    h.check(f"a backfill over {len(dates)} dates leaves {len(dates)} partitions", rc1 == 0 and not missing,
            [f"exit code {rc1}", f"{len(dates) - len(missing)} of {len(dates)} partitions present after the backfill"]
            + ([f"missing: {', '.join(missing[:5])}{' ...' if len(missing) > 5 else ''}"] if missing else [])
            + ["Writing one date must not touch the other dates."])

    changed = [d for d in dates if first[d] != second[d]]
    h.check("running the backfill again changes nothing", rc2 == 0 and not changed and not missing,
            [f"exit code {rc2}", f"{len(changed)} of {len(dates)} partitions changed on the second pass"]
            + (["(this check cannot pass while partitions are missing after the first pass)"] if missing else [])
            + [f"  aggs/dt={d}: {fmt(first[d][0])} -> {fmt(second[d][0])}" for d in changed[:4]])
    return h


if __name__ == "__main__":
    sys.exit(finish(run()))
