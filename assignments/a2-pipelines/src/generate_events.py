"""
Synthetic order and delivery events for the feature pipeline.

GIVEN. You do not need to read this file. `make data` runs it.

Writes two hive-partitioned event tables under data/events/:

    data/events/orders/dt=YYYY-MM-DD/data_0.parquet
    data/events/deliveries/dt=YYYY-MM-DD/data_0.parquet

An order's dt is the day it was placed. A delivery's dt is the day it was
delivered, which can be the day after the order (late-night orders). About 3% of
orders are cancelled and have no delivery event.

Everything is deterministic: the same arguments always produce the same bytes,
because every "random" number is derived from a hash of stable keys, never from a
random number generator.

    python -m src.generate_events                      # normal data
    python -m src.generate_events --shift prep_time_minutes=60 --shift-from 2026-03-10
"""

from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path

import duckdb

FIRST_DAY = date(2026, 1, 1)
LAST_DAY = date(2026, 3, 21)
N_RESTAURANTS = 400

ORDER_COLUMNS = {"cart_size", "cart_value"}
DELIVERY_COLUMNS = {"prep_time_minutes", "delivery_minutes", "distance_km"}


def generate(data_dir: Path, shift: dict[str, float] | None = None, shift_from: date | None = None) -> dict:
    events_dir = data_dir / "events"
    if events_dir.exists():
        shutil.rmtree(events_dir)
    events_dir.mkdir(parents=True)

    con = duckdb.connect()

    # A uniform in [0, 1) derived from a hash of (key, salt). Stable across runs.
    con.execute("CREATE MACRO u(key, salt) AS ((hash(key::VARCHAR || '|' || salt) % 1000003) / 1000003.0)")
    # A standard normal from two uniforms (Box-Muller).
    con.execute("CREATE MACRO z(key, salt) AS sqrt(-2 * ln(u(key, salt || 'a') + 1e-9)) * cos(2 * pi() * u(key, salt || 'b'))")

    con.execute(f"""
        CREATE TABLE restaurants AS
        SELECT
            'R' || lpad(i::VARCHAR, 3, '0')                        AS restaurant_id,
            8 + 22 * u(i, 'prep')                                   AS base_prep_minutes,
            10 + floor(41 * u(i, 'vol'))::INTEGER                   AS base_daily_orders,
            CASE WHEN i <> 17 AND hash(i::VARCHAR || '|open') % 25 = 0
                 THEN DATE '{FIRST_DAY}' + CAST(floor(80 * u(i, 'opened')) AS INTEGER)
                 ELSE DATE '2025-01-01' END                         AS opened_on
        FROM range(1, {N_RESTAURANTS + 1}) t(i)
    """)

    con.execute(f"""
        CREATE TABLE days AS
        SELECT d::DATE AS day FROM range(DATE '{FIRST_DAY}', DATE '{LAST_DAY}' + INTERVAL 1 DAY, INTERVAL 1 DAY) t(d)
    """)

    # One row per (restaurant, day) with that day's order count.
    con.execute("""
        CREATE TABLE volume AS
        SELECT r.restaurant_id, d.day,
               round(r.base_daily_orders
                     * CASE dayofweek(d.day) WHEN 5 THEN 1.06 WHEN 6 THEN 1.08 WHEN 1 THEN 0.95 ELSE 1.0 END
                     * (0.90 + 0.20 * u(r.restaurant_id || d.day, 'dayvol')))::INTEGER AS n_orders
        FROM restaurants r CROSS JOIN days d
        WHERE d.day >= r.opened_on
    """)

    # One row per order.
    con.execute("""
        CREATE TABLE orders_raw AS
        WITH o AS (
            SELECT v.restaurant_id, v.day, k,
                   v.restaurant_id || '-' || strftime(v.day, '%Y%m%d') || '-' || lpad(k::VARCHAR, 3, '0') AS order_id
            FROM volume v, LATERAL (SELECT unnest(generate_series(1, v.n_orders)) AS k)
        )
        SELECT
            order_id,
            restaurant_id,
            'Z' || lpad((1 + floor(12 * u(order_id, 'zone')))::INTEGER::VARCHAR, 2, '0') AS customer_zone,
            day + to_minutes(CAST(
                60 * CASE WHEN u(order_id, 'meal') < 0.15 THEN 9 + 13 * u(order_id, 'hr')
                          WHEN u(order_id, 'meal') < 0.50 THEN 11 + 3 * u(order_id, 'hr')
                          ELSE 17 + 6 * u(order_id, 'hr') END AS INTEGER))       AS placed_at,
            (1 + floor(5 * u(order_id, 'cart')))::INTEGER                             AS cart_size,
            round(9 + 38 * u(order_id, 'value') + 6 * u(order_id, 'value2'), 2)        AS cart_value,
            u(order_id, 'cancel') < 0.03                                               AS cancelled
        FROM o
    """)

    # One row per delivered order.
    con.execute("""
        CREATE TABLE deliveries_raw AS
        SELECT
            o.order_id,
            'D' || substr(md5(o.order_id), 1, 10)                                        AS delivery_id,
            'C' || lpad((1 + floor(900 * u(o.order_id, 'courier')))::INTEGER::VARCHAR, 3, '0') AS courier_id,
            o.placed_at,
            round(r.base_prep_minutes
                  * CASE WHEN hour(o.placed_at) BETWEEN 18 AND 20 THEN 1.25 WHEN hour(o.placed_at) BETWEEN 12 AND 13 THEN 1.10 ELSE 1.0 END
                  * CASE WHEN o.restaurant_id = 'R017' AND o.placed_at::DATE = DATE '2026-03-08' THEN 1.70 ELSE 1.0 END
                  * exp(0.18 * z(o.order_id, 'prep')), 1)                                  AS prep_time_minutes,
            round(0.4 + 7.6 * u(o.order_id, 'dist'), 2)                                    AS distance_km
        FROM orders_raw o JOIN restaurants r USING (restaurant_id)
        WHERE NOT o.cancelled
    """)
    con.execute("""
        CREATE TABLE deliveries_full AS
        SELECT *,
               round(prep_time_minutes + 3.2 * distance_km + 4 + 2.5 * abs(z(order_id, 'travel')), 1) AS delivery_minutes
        FROM deliveries_raw
    """)

    con.execute("""
        CREATE TABLE orders AS
        SELECT order_id, restaurant_id, customer_zone, placed_at, cart_size, cart_value, placed_at::DATE AS dt
        FROM orders_raw ORDER BY placed_at, order_id
    """)
    con.execute("""
        CREATE TABLE deliveries AS
        SELECT order_id, delivery_id, courier_id,
               placed_at + to_minutes(CAST(prep_time_minutes * 0.6 AS INTEGER))     AS accepted_at,
               placed_at + to_minutes(CAST(prep_time_minutes AS INTEGER))           AS ready_at,
               placed_at + to_minutes(CAST(delivery_minutes AS INTEGER))            AS delivered_at,
               prep_time_minutes, delivery_minutes, distance_km,
               (placed_at + to_minutes(CAST(delivery_minutes AS INTEGER)))::DATE     AS dt
        FROM deliveries_full ORDER BY delivered_at, order_id
    """)

    # Optional upstream change: scale one or more columns from a date onward.
    for column, factor in (shift or {}).items():
        table = "orders" if column in ORDER_COLUMNS else "deliveries" if column in DELIVERY_COLUMNS else None
        if table is None:
            raise SystemExit(f"--shift: unknown column {column!r}. Orders: {sorted(ORDER_COLUMNS)}. Deliveries: {sorted(DELIVERY_COLUMNS)}")
        con.execute(f"UPDATE {table} SET {column} = round({column} * {factor}, 3) WHERE dt >= DATE '{shift_from}'")

    con.execute(f"COPY orders TO '{events_dir / 'orders'}' (FORMAT parquet, PARTITION_BY (dt))")
    con.execute(f"COPY deliveries TO '{events_dir / 'deliveries'}' (FORMAT parquet, PARTITION_BY (dt))")

    n_orders = con.execute("SELECT count(*) FROM orders").fetchone()[0]
    n_deliveries = con.execute("SELECT count(*) FROM deliveries").fetchone()[0]
    n_days = con.execute("SELECT count(DISTINCT dt) FROM orders").fetchone()[0]
    return {"orders": n_orders, "deliveries": n_deliveries, "days": n_days, "first_day": FIRST_DAY, "last_day": LAST_DAY}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default="data")
    p.add_argument("--shift", action="append", default=[], metavar="COLUMN=FACTOR",
                   help="multiply COLUMN by FACTOR from --shift-from onward (repeatable)")
    p.add_argument("--shift-from", type=date.fromisoformat, default=None)
    a = p.parse_args(argv)

    shift = {}
    for s in a.shift:
        column, _, factor = s.partition("=")
        shift[column] = float(factor)
    if shift and a.shift_from is None:
        p.error("--shift needs --shift-from")

    info = generate(Path(a.data_dir), shift, a.shift_from)
    print(f"events: {info['orders']:,} orders, {info['deliveries']:,} deliveries, "
          f"{info['days']} days ({info['first_day']} to {info['last_day']})")
    if shift:
        print(f"upstream change applied from {a.shift_from}: {shift}")


if __name__ == "__main__":
    main()
