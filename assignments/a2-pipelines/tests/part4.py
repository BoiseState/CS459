"""Part 4 · yesterday was wrong. Your two queries, and a repair driven by what they say.

What this test can and cannot tell you: it checks that your queries run, that they have
the right shape, and that your repair is consistent with your own answer. It does not
tell you whether your answer is the right one. That is graded, against this history and
against an incident you have not seen. Convince yourself from the manifests.
"""

import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

from tests.common import DATA, REPO, Harness, cli, con_with_views, finish, fmt, partition_rows, reset_data

FIXTURE = REPO / "tests" / "fixtures" / "part4"
QUERIES = {
    "partition_status": ("queries/partition_status.sql", ["dt", "run_id", "git_sha", "status"]),
    "contaminated_models": ("queries/contaminated_models.sql", ["model_version", "bad_partitions"]),
}


def load_fixture(fixture: Path = FIXTURE) -> None:
    """Put the recorded history where this pipeline's own output goes."""
    shutil.copytree(fixture / "runs", DATA / "runs", dirs_exist_ok=True)
    shutil.copytree(fixture / "models", DATA / "models", dirs_exist_ok=True)
    shutil.copy(fixture / "incident.json", DATA / "incident.json")


def facts_about(runs_dir: Path, bad_sha: str) -> dict:
    """Two facts read straight off the manifests, used to check the shape of an answer.

    Neither is the answer: which run owns a partition now is the part you work out.
    """
    published, touched_by_bad = set(), set()
    for f in sorted(runs_dir.glob("*.json")):
        m = json.loads(f.read_text())
        if m.get("outputs_written") == [f"aggs/dt={m['dt']}"]:
            published.add(m["dt"])
            if m.get("git_sha") == bad_sha:
                touched_by_bad.add(m["dt"])
    return {"published": published, "touched_by_bad": touched_by_bad}


def run_query(con, sql: str, want_cols: list[str]) -> set[tuple[str, ...]]:
    rel = con.sql(sql)
    got_cols = [c.lower() for c in rel.columns]
    if got_cols != want_cols:
        raise ValueError(f"columns are {got_cols}, expected {want_cols}")
    return {tuple(str(v) for v in row) for row in rel.fetchall()}


def student_query(name: str) -> str:
    return (REPO / QUERIES[name][0]).read_text()


def run(fixture: Path = FIXTURE) -> Harness:
    h = Harness("part 4", "yesterday was wrong")
    reset_data()
    load_fixture(fixture)
    facts = facts_about(DATA / "runs", json.loads((DATA / "incident.json").read_text())["bad_sha"])

    present = {name: (REPO / path).exists() for name, (path, _) in QUERIES.items()}
    h.check("both query files exist", all(present.values()),
            [f"{'found' if ok else 'MISSING'}: {QUERIES[n][0]}" for n, ok in present.items()])
    if not all(present.values()):
        return h

    con = con_with_views()
    results: dict[str, set | Exception] = {}
    for name, (path, cols) in QUERIES.items():
        try:
            results[name] = run_query(con, student_query(name), cols)
        except Exception as e:
            results[name] = e

    broken = {n: e for n, e in results.items() if isinstance(e, Exception)}
    if not h.check("both queries run and return the required columns", not broken,
                   [f"{QUERIES[n][0]}: {type(e).__name__}: {e}" for n, e in broken.items()]):
        return h

    status, models = results["partition_status"], results["contaminated_models"]
    bad = sorted(date.fromisoformat(r[0]) for r in status if r[3] == "bad")

    h.check("partition_status has one row per date that was ever published",
            len(status) == len(facts["published"]),
            [f"your query returned {len(status)} rows; {len(facts['published'])} dates were ever written to aggs/",
             "A run that failed wrote nothing, so it owns nothing."])

    h.check("the partitions you call bad were written by the bad commit at some point",
            set(str(d) for d in bad) <= facts["touched_by_bad"],
            [f"you marked {len(bad)} bad; the bad commit only ever wrote {len(facts['touched_by_bad'])} partitions",
             f"not written by it: {', '.join(sorted(set(str(d) for d in bad) - facts['touched_by_bad'])[:6])}"])

    h.note(f"your query marks {len(bad)} partition(s) bad: {', '.join(str(d) for d in bad) or 'none'}")
    h.note(f"your query names {len(models)} contaminated model version(s): "
           + (", ".join(sorted(m[0] for m in models)) or "none"))
    h.note("whether those are the right ones is graded later, here and on an incident you have not seen")
    if not bad:
        return h

    # The repair, driven by the student's own query: backfill exactly the dates it calls bad.
    ranges, start = [], None
    for i, d in enumerate(bad):
        if start is None:
            start = d
        if i + 1 == len(bad) or bad[i + 1] != d + timedelta(days=1):
            ranges.append((start, d)); start = None

    # Twice, on purpose. At 2am the retry will do this to you.
    rows_after_first, rc = {}, 0
    for pass_no in (1, 2):
        for s, e in ranges:
            code, out = cli("--backfill", str(s), str(e))
            rc = rc or code
        if pass_no == 1:
            rows_after_first = {d: partition_rows(d) for d in bad}
    rows_after_second = {d: partition_rows(d) for d in bad}
    h.check("the repair backfill runs, and running it again changes nothing",
            rc == 0 and rows_after_first == rows_after_second and all(rows_after_first.values()),
            [f"exit code {rc}"] + [f"  aggs/dt={d}: {fmt(rows_after_first[d])} -> {fmt(rows_after_second[d])}"
                                   for d in bad if rows_after_first[d] != rows_after_second[d] or not rows_after_first[d]][:4]
            + ["A backfill is a re-run. It is only safe if a re-run is safe (Part 1)."])

    con = con_with_views()
    after = run_query(con, student_query("partition_status"), QUERIES["partition_status"][1])
    still_bad = sorted(r[0] for r in after if r[3] == "bad")
    h.check("after the repair, your own query reports no bad partitions",
            not still_bad and len(after) == len(status),
            [f"your query now returns {len(after)} rows, {len(still_bad)} still marked bad"]
            + ([f"still bad: {', '.join(still_bad[:6])}"] if still_bad else [])
            + ["You repaired the dates your query named. If it still calls them bad, it is not reading",
               "which run owns the partition now."])

    models_after = run_query(con, student_query("contaminated_models"), QUERIES["contaminated_models"][1])
    h.check("after the repair, contaminated_models is unchanged", models_after == models,
            [f"before the repair: {len(models)} model versions, after: {len(models_after)}",
             "Repairing the table does not repair the models that already learned from it.",
             "A model read a particular run's output. Backfilling later does not change what it read."])
    return h


if __name__ == "__main__":
    sys.exit(finish(run()))
