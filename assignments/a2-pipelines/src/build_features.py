"""
The nightly feature job. THIS IS THE FILE YOU FIX.

Four stages, one partition per date. For a date D it builds `aggs/dt=D`: one row
per restaurant with that restaurant's rolling statistics, which is the feature
vector for any order placed on D.

    1. read_events      read the raw orders and deliveries this run needs
    2. join_deliveries  join them, drop orders that have no delivery
                        (the gates in src/gates.py run here)
    3. rolling_aggs     per-restaurant statistics over a trailing window
    4. write_aggs       publish the partition to the feature table

Each stage gets a Context (see src/runner.py) and writes its output into
`ctx.stage_dir`. The next stage reads it with `ctx.output_of("<stage>")`.

Every value in aggs/dt=D must be something that was knowable before D began:
the row is used to predict orders placed on D, so it may not contain anything
from D itself.
"""

from datetime import timedelta

from src.runner import stage

WINDOW_DAYS = 30            # the trailing window for every rolling feature
LATE_THRESHOLD_MINUTES = 45  # a delivery slower than this counts as late


@stage("read_events")
def read_events(ctx):
    """Stage 1. Read the raw events this run needs: the target date and its trailing window."""
    window_start = ctx.dt - timedelta(days=WINDOW_DAYS)

    # Orders start one day earlier than deliveries, so a delivery on the first day of
    # the window can still find the order it belongs to.
    orders = ctx.events("orders", window_start - timedelta(days=1), ctx.dt)
    deliveries = ctx.events("deliveries", window_start, ctx.dt)

    ctx.con.execute(f"COPY (SELECT * FROM {orders}) TO '{ctx.stage_dir}/orders.parquet' (FORMAT parquet)")
    ctx.con.execute(f"COPY (SELECT * FROM {deliveries}) TO '{ctx.stage_dir}/deliveries.parquet' (FORMAT parquet)")


@stage("join_deliveries", after="read_events")
def join_deliveries(ctx):
    """Stage 2. One row per completed delivery. An order with no delivery is not a row you can learn from."""
    src = ctx.output_of("read_events")
    ctx.con.execute(f"""
        COPY (
            SELECT
                o.order_id,
                o.restaurant_id,
                o.customer_zone,
                o.placed_at,
                o.cart_size,
                o.cart_value,
                d.delivered_at,
                d.dt                 AS delivery_date,
                d.prep_time_minutes,
                d.delivery_minutes,
                d.distance_km
            FROM read_parquet('{src}/orders.parquet') AS o
            JOIN read_parquet('{src}/deliveries.parquet') AS d USING (order_id)
            ORDER BY d.delivered_at, o.order_id
        ) TO '{ctx.stage_dir}/joined.parquet' (FORMAT parquet)
    """)


@stage("rolling_aggs", after="join_deliveries")
def rolling_aggs(ctx):
    """Stage 3. Per-restaurant rolling statistics, then keep only the target date's row."""
    joined = ctx.output_of("join_deliveries") / "joined.parquet"
    ctx.con.execute(f"""
        COPY (
            WITH daily AS (
                -- one row per restaurant per day it had deliveries
                SELECT
                    restaurant_id,
                    delivery_date                                            AS dt,
                    count(*)                                                 AS n_deliveries,
                    sum(prep_time_minutes)                                   AS prep_sum,
                    sum(delivery_minutes)                                    AS delivery_sum,
                    sum(CASE WHEN delivery_minutes > {LATE_THRESHOLD_MINUTES} THEN 1 ELSE 0 END) AS n_late
                FROM read_parquet('{joined}')
                GROUP BY restaurant_id, delivery_date
            ),
            rolling AS (
                SELECT
                    restaurant_id,
                    dt,
                    coalesce(sum(n_deliveries) OVER w, 0)                        AS restaurant_deliveries_30d,
                    sum(prep_sum)     OVER w / nullif(sum(n_deliveries) OVER w, 0) AS restaurant_prep_avg_30d,
                    sum(delivery_sum) OVER w / nullif(sum(n_deliveries) OVER w, 0) AS restaurant_delivery_avg_30d,
                    sum(n_late)       OVER w / nullif(sum(n_deliveries) OVER w, 0) AS restaurant_late_rate_30d
                FROM daily
                WINDOW w AS (
                    PARTITION BY restaurant_id
                    ORDER BY dt
                    RANGE BETWEEN INTERVAL {WINDOW_DAYS} DAY PRECEDING AND CURRENT ROW
                )
            )
            SELECT
                restaurant_id,
                dt,
                restaurant_deliveries_30d::INTEGER            AS restaurant_deliveries_30d,
                round(restaurant_prep_avg_30d, 4)             AS restaurant_prep_avg_30d,
                round(restaurant_delivery_avg_30d, 4)         AS restaurant_delivery_avg_30d,
                round(restaurant_late_rate_30d, 4)            AS restaurant_late_rate_30d
            FROM rolling
            WHERE dt = DATE '{ctx.dt}'
            ORDER BY restaurant_id
        ) TO '{ctx.stage_dir}/aggs.parquet' (FORMAT parquet)
    """)


@stage("write_aggs", after="rolling_aggs")
def write_aggs(ctx):
    """Stage 4. Publish the partition to the feature table, stamped with the run that produced it."""
    aggs = ctx.output_of("rolling_aggs") / "aggs.parquet"
    ctx.con.execute(f"""
        COPY (SELECT *, '{ctx.run_id}' AS run_id FROM read_parquet('{aggs}'))
        TO '{ctx.aggs_dir}' (FORMAT parquet, PARTITION_BY (dt), APPEND)
    """)
