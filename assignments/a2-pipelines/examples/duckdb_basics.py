"""
Every DuckDB feature this assignment needs, in one runnable file.

    python -m examples.duckdb_basics

DuckDB is an in-process SQL database: no server, nothing to start. You open a
connection, run SQL, and get results back. It reads and writes parquet files
directly, so the "database" is just the files under data/.

Run this after `make data`. Read it top to bottom; it takes about fifteen minutes.
"""

import os
import tempfile
from pathlib import Path

import duckdb

DATA = Path(os.environ.get("PIPELINE_DATA_DIR", "data")).resolve()

con = duckdb.connect()   # in memory. Nothing is saved except what you COPY to a file.


# 1. Reading a partitioned table -------------------------------------------------
#
# data/events/orders/ holds one folder per date: dt=2026-01-01/, dt=2026-01-02/, ...
# That layout is called hive partitioning. A glob reads them all, and
# hive_partitioning = true turns the folder name into a column called dt.

orders = f"read_parquet('{DATA}/events/orders/*/*.parquet', hive_partitioning = true)"

print("-- 1. one query over 80 daily folders")
con.sql(f"""
    SELECT dt, count(*) AS orders, round(avg(cart_value), 2) AS avg_cart
    FROM {orders}
    WHERE dt BETWEEN DATE '2026-03-01' AND DATE '2026-03-03'
    GROUP BY dt ORDER BY dt
""").show()
# Because dt is a folder name, that WHERE clause never opens the other 77 folders.


# 2. Getting results into Python ---------------------------------------------------

print("-- 2. fetchone / fetchall")
n = con.execute(f"SELECT count(*) FROM {orders} WHERE dt = DATE '2026-03-03'").fetchone()[0]
print(f"   {n:,} orders on 2026-03-03")
rows = con.execute(f"SELECT restaurant_id, count(*) FROM {orders} WHERE dt = DATE '2026-03-03' GROUP BY 1 ORDER BY 2 DESC LIMIT 3").fetchall()
print(f"   busiest: {rows}")


# 3. Joining two tables ------------------------------------------------------------

deliveries = f"read_parquet('{DATA}/events/deliveries/*/*.parquet', hive_partitioning = true)"

print("-- 3. join orders to deliveries; an inner join drops orders that have no delivery")
con.sql(f"""
    SELECT count(*) AS orders, count(d.order_id) AS delivered, count(*) - count(d.order_id) AS never_delivered
    FROM {orders} AS o
    LEFT JOIN {deliveries} AS d USING (order_id)
    WHERE o.dt = DATE '2026-03-03'
""").show()


# 4. Window functions ---------------------------------------------------------------
#
# A window function computes something over a set of rows *related to the current
# row* without collapsing them the way GROUP BY does. The frame says which rows.
# ROWS counts rows; RANGE uses the ORDER BY value, so gaps in dates are handled.

print("-- 4. a 3-day running total per restaurant, and a per-date rank")
con.sql(f"""
    WITH daily AS (
        SELECT restaurant_id, dt, count(*) AS n
        FROM {orders}
        WHERE restaurant_id IN ('R001', 'R002') AND dt BETWEEN DATE '2026-03-01' AND DATE '2026-03-05'
        GROUP BY restaurant_id, dt
    )
    SELECT restaurant_id, dt, n,
           sum(n) OVER (PARTITION BY restaurant_id ORDER BY dt ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS n_3day,
           rank() OVER (PARTITION BY dt ORDER BY n DESC) AS rank_on_day
    FROM daily ORDER BY restaurant_id, dt
""").show()
# Read the frame clause slowly: "ROWS BETWEEN 2 PRECEDING AND CURRENT ROW" says exactly
# which rows are in the sum. Every rolling feature in the pipeline is one of these.


# 5. Writing files -----------------------------------------------------------------

tmp = Path(tempfile.mkdtemp())
print(f"-- 5. writing parquet under {tmp}")

# A single file. Writing to an existing file name replaces it.
con.execute(f"COPY (SELECT 1 AS x) TO '{tmp}/one.parquet' (FORMAT parquet)")

# A partitioned table: one folder per value of the PARTITION_BY column.
con.execute(f"""
    COPY (SELECT DATE '2026-03-01' + i::INTEGER AS dt, i AS x FROM range(3) t(i))
    TO '{tmp}/table' (FORMAT parquet, PARTITION_BY (dt))
""")
print("   wrote:", sorted(str(p.relative_to(tmp)) for p in tmp.rglob("*.parquet")))

# Writing into that folder a second time is where you have to decide something.
# Try it and read the error. The options are in the DuckDB docs under "partitioned writes".
try:
    con.execute(f"COPY (SELECT DATE '2026-03-01' AS dt, 9 AS x) TO '{tmp}/table' (FORMAT parquet, PARTITION_BY (dt))")
except duckdb.IOException as e:
    print("   second write refused:", str(e).splitlines()[0])


# 6. Reading JSON -------------------------------------------------------------------
#
# The run manifests are JSON. DuckDB reads a folder of them as one table, and
# unnest() turns a list column into one row per element.

runs = DATA / "runs"
if runs.exists() and any(runs.glob("*.json")):
    print("-- 6. the run manifests as a table")
    con.sql(f"""
        SELECT run_id, dt, status, rows_out, unnest(outputs_written) AS wrote
        FROM read_json('{runs}/*.json', union_by_name = true)
        ORDER BY finished_at DESC LIMIT 5
    """).show()
else:
    print("-- 6. (no run manifests yet: run the pipeline once and re-run this file)")

print("done. `make sql` gives you a prompt with all of these tables ready as views.")
