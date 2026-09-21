"""`make peek DATE=2026-03-08`: summary statistics for one date. GIVEN.

Shows the input events for that date and the feature table partition, if it exists.
This is how you look at data without a file browser.
"""

import os
import sys
from pathlib import Path

import duckdb

DATA = Path(os.environ.get("PIPELINE_DATA_DIR", "data")).resolve()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: make peek DATE=YYYY-MM-DD"); return 2
    dt = sys.argv[1]
    con = duckdb.connect()

    print(f"== input events for {dt}")
    orders = f"read_parquet('{DATA}/events/orders/dt={dt}/*.parquet')"
    deliveries = f"read_parquet('{DATA}/events/deliveries/dt={dt}/*.parquet')"
    try:
        n_o = con.execute(f"SELECT count(*) FROM {orders}").fetchone()[0]
        n_d = con.execute(f"SELECT count(*) FROM {deliveries}").fetchone()[0]
        print(f"   {n_o:,} orders placed, {n_d:,} deliveries completed")
        con.sql(f"""
            SELECT col, round(min(v), 1) AS min, round(quantile_cont(v, 0.5), 1) AS p50, round(avg(v), 1) AS mean,
                   round(quantile_cont(v, 0.95), 1) AS p95, round(max(v), 1) AS max, count(*) - count(v) AS nulls
            FROM (
                SELECT 'prep_time_minutes' AS col, prep_time_minutes AS v FROM {deliveries}
                UNION ALL SELECT 'delivery_minutes', delivery_minutes FROM {deliveries}
                UNION ALL SELECT 'distance_km', distance_km FROM {deliveries}
                UNION ALL SELECT 'cart_size', cart_size FROM {orders}
                UNION ALL SELECT 'cart_value', cart_value FROM {orders}
            ) GROUP BY col ORDER BY col
        """).show()
    except duckdb.IOException:
        print("   no events for this date. Run `make data`, or check the date (2026-01-01 to 2026-03-21).")

    print(f"== feature table aggs/dt={dt}")
    part = DATA / "aggs" / f"dt={dt}"
    if not list(part.glob("*.parquet")):
        print("   not written yet. Run: python -m src.runner --date " + dt)
        q = DATA / "quarantine" / f"dt={dt}"
        if list(q.glob("*.parquet")):
            print(f"   (but quarantine/dt={dt} exists: a gate sent it there)")
        return 0
    con.sql(f"""
        SELECT count(*) AS restaurants, count(DISTINCT run_id) AS runs_that_wrote_it,
               round(avg(restaurant_prep_avg_30d), 2) AS mean_prep_avg_30d,
               round(avg(restaurant_delivery_avg_30d), 2) AS mean_delivery_avg_30d,
               count(*) - count(restaurant_prep_avg_30d) AS null_prep_avg
        FROM read_parquet('{part}/*.parquet')
    """).show()
    con.sql(f"SELECT * FROM read_parquet('{part}/*.parquet') ORDER BY restaurant_id LIMIT 5").show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
