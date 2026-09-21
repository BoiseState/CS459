"""
Data gates. THIS IS THE OTHER FILE YOU EDIT (Part 3).

A gate is a function that looks at one date's joined deliveries (the output of
stage 2) and decides whether the pipeline should trust them. Every gate runs on
every date, after stage 2 and before stage 3.

A gate is registered with the @gate decorator and declares what the runner does
when it fires:

    on_fail="fail"        stop the run, exit non-zero, write nothing for this date
    on_fail="warn"        write the partition anyway, record the warning in the manifest
    on_fail="quarantine"  write the partition to data/quarantine/ instead of data/aggs/
    on_fail=None          not decided. The runner treats this as "warn" and records that
                          nobody chose. Warn-and-continue is what you get by not deciding.

A gate receives:

    ctx      the run Context (src/runner.py). ctx.dt is the date being built,
             ctx.con is a DuckDB connection.
    joined   the name of a view over this date's stage 2 output. Its columns are:
             order_id, restaurant_id, customer_zone, placed_at, cart_size, cart_value,
             delivered_at, delivery_date, prep_time_minutes, delivery_minutes, distance_km
             It holds the trailing window too, so `WHERE delivery_date = ctx.dt` is today
             and earlier dates are history you can compare against.

and returns a GateResult(passed, observed, expected, detail). Everything but
`passed` is just recorded in the manifest so a person can see why it fired.
"""

from src.runner import GateResult, gate


@gate(name="rows_in_vs_trailing_7d", on_fail=None)
def rows_in_vs_trailing_7d(ctx, joined) -> GateResult:
    """Today's delivery count must be within 15% of the mean of the previous 7 days.

    This is the check from the in-class incident. Read that slide again before you
    trust it with anything.
    """
    today = ctx.con.execute(f"""
        SELECT count(*) FROM {joined} WHERE delivery_date = DATE '{ctx.dt}'
    """).fetchone()[0]

    trailing = ctx.con.execute(f"""
        SELECT avg(n) FROM (
            SELECT count(*) AS n
            FROM {joined}
            WHERE delivery_date BETWEEN DATE '{ctx.dt}' - INTERVAL 7 DAY AND DATE '{ctx.dt}' - INTERVAL 1 DAY
            GROUP BY delivery_date
        )
    """).fetchone()[0]

    if trailing is None:
        # The first days of the dataset have nothing to compare against.
        return GateResult(passed=True, observed=today, expected=None, detail="no trailing history yet")

    ratio = today / trailing
    return GateResult(
        passed=abs(ratio - 1) <= 0.15,
        observed=today,
        expected=f"{trailing:.0f} +/- 15%",
        detail=f"today / trailing 7-day mean = {ratio:.3f}",
    )

