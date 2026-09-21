# Rubric

100 points. Tests 40, writeup 35, code review 20, AI use log 5.

## Tests (40)

Each part's tests are run exactly as `make partN` runs them, plus the unseen variants
for Parts 3 and 4. Points within a part are split evenly across its checks.

| Part | Points | Includes |
|---|---|---|
| Part 1 | 10 | same date twice; backfill leaves every date; second backfill changes nothing |
| Part 2 | 10 | oracle match; the new restaurant's NULL |
| Part 3 | 10 | gate declared; no crashes; fires on the change; quiet before it; **the same four on an unseen variant** |
| Part 4 | 10 | 4 for shape and self-consistency (queries run, one row per published date, repair safe to re-run, their own answer holds after it) on this history and on an unseen one; **6 for the answers actually being right**, checked at grading against both histories |

## Writeup (35)

One section per part. Graded on whether the explanation is correct, specific to this
pipeline, and shows the cause was understood rather than the symptom.

| Section | Points | Full credit looks like |
|---|---|---|
| Part 0 | 3 | One prediction per failing part, written before reading code. Wrong predictions are fine. Missing predictions are not |
| Part 1 | 6 | Names the mechanism (a second write adds instead of replaces). States the retry loop's assumption (a stage can be re-entered with no cleanup) and points to `run_stage` in `runner.py` |
| Part 2 | 6 | Says what leaked (the target date's own deliveries) and why the offline error improved (the feature encodes the answer). Explains the NULL as correct, with the reason |
| Part 3 | 8 | Identifies the changed column and magnitude. Explains why a row count cannot see a value change. Each `on_fail` choice is justified by what reads the table downstream and by who gets woken up. Answers the trailing-window question honestly (a trailing comparison absorbs a level shift within days; a fixed reference does not) |
| Part 4 | 7 | Correct list of bad partitions with the two non-obvious ones (March 2 and March 9) explained from the manifests. States why the models stay contaminated after repair and what retraining would cost |
| Part 5 | 5 | Partition 31: describes the mixed table (new, old, and one half-written), and proposes a write pattern that keeps readers safe (stage then swap, or a marker readers check). Next incident: a real gap in this pipeline and a check that would catch it, with a reason for that check over alternatives |

Deduct for answers that could have been written without running the code (generic
explanations of idempotency with nothing from this repo in them).

## Code review (20)

Read the diff of `src/build_features.py`, `src/gates.py`, and `queries/`.

| | Points | Full credit | Zero credit |
|---|---|---|---|
| Part 1 fix | 6 | The write itself is idempotent. One option changed, or an equivalent one-place change | Duplicates removed after the write. A delete-then-append that is not atomic. `OVERWRITE` (destroys other dates; fails the backfill check anyway) |
| Part 2 fix | 4 | The frame's upper bound excludes the target date. Nothing else in stage 3 changed | The NULL "fixed" by coalescing to today's value or to zero. A `ROWS` frame that happens to pass for R017 |
| Part 3 gate | 6 | Compares a distribution statistic across numeric columns against history. Handles the no-history days. Threshold has a stated reason | Checks one hard-coded column against one hard-coded number tuned to 60x |
| Part 4 queries | 4 | Readable, reads the SHA from `incident.json`, picks the latest successful writer per date | Hard-coded dates or SHA. Counts failed runs as writers |

Small, readable diffs score higher than large ones. A fix that touches a file the
spec says not to change scores zero for that part (the grader replaces those files
anyway, so the fix would not have run).

## AI use log (5)

Pass/fail on completeness: the table, the inline comments where AI-generated code
was kept, and one documented case where the AI was wrong. The amount of AI use is
not graded and does not affect any other score.
