"""Part 2 · it knew the future. One feature, one restaurant, one date, against what was knowable."""

import sys
from datetime import date, timedelta

import duckdb

from tests.common import DATA, Harness, cli, finish, partition_dir, reset_data

FEATURE = "restaurant_prep_avg_30d"
RESTAURANT = "R017"
DT = date(2026, 3, 8)
WINDOW_DAYS = 30
NEW_RESTAURANT = "R208"      # opened on DT, so it has no history at all


def oracle(restaurant: str, dt: date) -> float | None:
    """The feature by its definition: the average prep time over the 30 days before dt, not including dt.

    Computed straight from the raw events, without the pipeline.
    """
    start, end = dt - timedelta(days=WINDOW_DAYS), dt - timedelta(days=1)
    return duckdb.sql(f"""
        SELECT round(avg(d.prep_time_minutes), 4)
        FROM read_parquet('{DATA}/events/deliveries/*/*.parquet', hive_partitioning = true) AS d
        JOIN read_parquet('{DATA}/events/orders/*/*.parquet', hive_partitioning = true) AS o USING (order_id)
        WHERE o.restaurant_id = '{restaurant}' AND d.dt BETWEEN DATE '{start}' AND DATE '{end}'
    """).fetchone()[0]


def computed(restaurant: str, dt: date):
    d = partition_dir(dt)
    if not list(d.glob("*.parquet")):
        return "no partition"
    row = duckdb.sql(f"SELECT {FEATURE} FROM read_parquet('{d}/*.parquet') WHERE restaurant_id = '{restaurant}'").fetchall()
    return row[0][0] if row else "no row"


def run() -> Harness:
    h = Harness("part 2", "it knew the future")
    reset_data()
    rc, out = cli("--date", str(DT))
    h.check("the pipeline runs the date", rc == 0, out.strip().splitlines()[-8:])

    got, want = computed(RESTAURANT, DT), oracle(RESTAURANT, DT)
    ok = isinstance(got, float) and abs(got - want) < 0.005
    h.check(f"{FEATURE} for {RESTAURANT} on {DT} matches what was knowable", ok, [
        f"{FEATURE}  restaurant_id={RESTAURANT}  dt={DT}",
        f"  computed : {got}",
        f"  correct  : {want}",
        "This feature contains information that was not available at prediction time.",
    ])

    got_new = computed(NEW_RESTAURANT, DT)
    h.check(f"{NEW_RESTAURANT}, which opened on {DT}, has no value yet", got_new is None, [
        f"{FEATURE}  restaurant_id={NEW_RESTAURANT}  dt={DT}",
        f"  computed : {got_new}",
        f"  correct  : NULL",
        f"{NEW_RESTAURANT}'s first delivery was on {DT}. Before that day there is nothing to average.",
    ])
    return h


if __name__ == "__main__":
    sys.exit(finish(run()))
