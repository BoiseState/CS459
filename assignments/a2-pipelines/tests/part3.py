"""Part 3 · nothing errored. An upstream change on one date. Your gate must fire that day and stay quiet before it."""

import sys
from datetime import date, timedelta

from tests.common import EXAMPLE_GATE, Harness, finish, reset_data, run_in_process

# The visible incident. At grading, a variant with a different column, factor and date runs too.
CHANGE_DATE = date(2026, 3, 10)
CHANGE = {"prep_time_minutes": 60.0}
FIRST_DATE = date(2026, 1, 1)


def run(change_date: date = CHANGE_DATE, change: dict = CHANGE, first_date: date = FIRST_DATE) -> Harness:
    h = Harness("part 3", "nothing errored")
    reset_data(shift=change, shift_from=change_date)

    from src import gates as _gates  # noqa: F401  (registers the gates)
    from src.runner import GATES

    yours = [g for g in GATES if g.name != EXAMPLE_GATE]
    h.check("you added at least one gate in src/gates.py", bool(yours),
            [f"gates registered: {[g.name for g in GATES]}"])
    undecided = [g.name for g in GATES if g.on_fail is None]
    h.check("every gate declares on_fail", not undecided,
            [f"on_fail is None for: {undecided}", "Warn-and-continue is what you get by not deciding. Decide."])

    # The dates the gates must be quiet on: the first days of the data, when there is
    # little or no history, and the 30 days leading up to the change. Then the change.
    dates = sorted({first_date + timedelta(days=i) for i in range(5)}
                   | {change_date - timedelta(days=i) for i in range(31)})
    print(f"        running {len(dates)} dates: {dates[0]} to {dates[4]}, then {dates[5]} to {dates[-1]} ...", end="", flush=True)
    fired: dict[date, list[dict]] = {}
    errors: dict[date, str] = {}
    statuses: dict[date, dict] = {}
    for d in dates:
        m = run_in_process(d)
        statuses[d] = m
        if m["status"] == "failed" and m["error"] and not m["error"].startswith("gate failed"):
            errors[d] = m["error"]
        fired[d] = [c for c in m["checks"] if c["status"] == "fail"]
    print(" done")

    h.check("no gate crashed on any date", not errors,
            [f"{d}: {e}" for d, e in list(errors.items())[:3]]
            + ["A gate that raises on a quiet day is worse than no gate: it takes the run down with it."])

    on_day = [c for c in fired.get(change_date, []) if c["gate"] != EXAMPLE_GATE]
    example_on_day = [c for c in fired.get(change_date, []) if c["gate"] == EXAMPLE_GATE]
    h.check(f"your gate fires on {change_date}", bool(on_day), [
        f"upstream change on {change_date}: {', '.join(f'{k} x {v:g}' for k, v in change.items())}",
        f"the example gate ({EXAMPLE_GATE}) {'fired' if example_on_day else 'passed'} that day",
        "your gate(s) passed. The pipeline succeeded. Nothing caught it.",
    ])
    if on_day:
        for c in on_day:
            h.note(f"{c['gate']} fired: observed={c['observed']} expected={c['expected']} {c['detail'] or ''}".rstrip())
        h.note(f"run status on {change_date}: {statuses[change_date]['status']}"
               + (f"  ({statuses[change_date]['error']})" if statuses[change_date]["error"] else "")
               + (f"  outputs_written={statuses[change_date]['outputs_written']}"))

    noisy = {d: c for d, c in fired.items() if d < change_date and c}
    h.check(f"every gate is quiet on every date before {change_date}", not noisy,
            [f"{len(noisy)} of {len(dates) - 1} earlier dates had a gate fire"]
            + [f"  {d}: {', '.join(c['gate'] + ' (observed=' + str(c['observed']) + ')' for c in cs)}"
               for d, cs in list(noisy.items())[:5]]
            + ["A gate that fires on normal days gets ignored by the people it pages."])
    return h


if __name__ == "__main__":
    sys.exit(finish(run()))
