# Assignment 2: Pipelines

**CS 459 · Machine Learning in Production**
**Released:** Friday, September 18 · **Due:** Monday, October 5, 11:59pm (Mountain)
**Expected effort:** 4 to 6 hours · **AI use:** Scenario 4, Open GenAI with Accountability

---

## The situation

You just joined the ML platform team at the food delivery company from Week 2. The
nightly job that builds the restaurant feature table (`aggs`) is now yours. It feeds
both things on the architecture diagram we have been drawing since Week 2: the 50 ms
request path that shows customers an ETA, and the training pipeline that retrains the
ETA model every week.

The job works. Its happy-path test passes. It will also fail you four different ways
in your first week, and each of those failures has a test in this repo. Your job is to
make each one survivable, and then explain what you did and why.

You are not building a pipeline from scratch. You are **diagnosing and repairing** one
that someone else wrote. Most of the fixes are small. Finding them, and understanding
why they matter, is the assignment.

---

## How every part is written

Each part has the same fields, so you always know what is being asked:

| Field | What it tells you |
|---|---|
| **Incident** | What went wrong, as the team would describe it the next morning |
| **From lecture** | Which idea from class this is |
| **Run** | The command that reproduces it |
| **You'll see** | What the failure looks like |
| **Change** | Which file you edit, and what is off limits |
| **Done when** | Exactly what has to be true for the part to pass |
| **Write** | What goes in your writeup for this part |

Every `make partN` command starts from a clean copy of the data. You cannot break one
part by running another, and you can re-run any part as often as you like.

---

## Rules

**You may change:** `src/build_features.py`, `src/gates.py`, and anything you create
under `queries/`.

**Do not change anything else.** The grader replaces `tests/`, `tools/`, `examples/`,
`src/runner.py`, `src/generate_events.py`, the `Makefile` and the lockfile with its
own copies before running your code. If your solution depends on editing one of
those, it will not work at grading time.

**The command-line interface is fixed.** The tests call the runner with `--date`,
`--backfill`, `--resume`, `--force`, and `--retries`. Do not rename or remove them.

**Pull before every session.** Run `git pull` before you start working. If something
in the repo gets fixed after release, it will be listed in `CHANGELOG.md`.

---

## What to read, and what to skip

This repo has more code than you need to read. Spend your reading time here:

| File | How closely | Why |
|---|---|---|
| `examples/duckdb_basics.py` | Run it and read it (15 min) | Every DuckDB feature you need, in one file |
| `src/build_features.py` | Closely | The pipeline. Parts 1 and 2 are fixed here |
| `src/gates.py` | Closely | Part 3. Contains one worked example gate |
| `src/runner.py` | The top half | What a stage receives, how gates are applied, and the retry loop in `run_stage` |
| `data/runs/*.json` | Read the output, not the code | The run manifest. You will query these in Part 4 |

You do **not** need to read `src/generate_events.py` or anything in `tests/` or
`tools/`. They exist so the pipeline is complete. The test output tells you
everything the tests check.

A note on DuckDB: the version in this repo is pinned. Syntax you find online or get
from an AI assistant may be for a different version. When in doubt, check against
`examples/duckdb_basics.py`, which is known to work.

---

## Part 0 · Get it running, and predict

**Time:** about 60 minutes, most of it reading.

1. Follow the setup steps in `README.md`. You are set up when `make doctor` prints
   `all checks passed`.
2. Run `make test`. Every part except the happy path will fail. That is expected.
3. **Before you open any code**, write down one sentence per failing part: what do
   you think is wrong? You will be graded on having made a prediction, not on whether
   it was right. Being wrong and finding out why is the point.
4. Now read the files listed above.

**Write:** A table with one row per part: what the test output said, and your
prediction. Keep your original predictions even after you learn the answers.

---

## Part 1 · It ran twice

**Time:** about 30 minutes.

**Incident.** The 2am job failed partway through. The automatic retry fired at 2:45
and succeeded. The next morning, the feature table has two copies of every row for
March 3rd, and the 30-day averages built on top of it are wrong. Nothing errored and
no alert fired.

**From lecture.** Constraint 2: it ran twice. Retries are the only recovery mechanism
you have, so a pipeline you cannot safely re-run is a pipeline you cannot operate.

**Run.** `make part1`

**You'll see.** The pipeline runs the same date twice, and the row count for that date
doubles. Then a two-week backfill runs twice: every date has to survive the first
pass, and the second pass has to change nothing.

**Change.** Stage 4 (`write_aggs`) in `src/build_features.py`. Fix the write so that a
second run **cannot create** a duplicate. Removing duplicates after they are written
does not count, even if the test passes.

**Done when.** `make part1` passes: the same date run twice is unchanged, the backfill
leaves every date in place, and running it again changes nothing. There is more than
one way to write into a folder that already exists. One of them passes the first
check and fails the second.

**Write.** Why did a second run double the data? The runner retries a failed stage up
to three times. What does that assume about the code inside each stage, and where in
`runner.py` is that assumption made?

---

## Part 2 · It knew the future

**Time:** about 45 minutes.

**Incident.** The ETA model's offline error looks excellent. In production it is
noticeably worse. Someone suspects one of the features.

**From lecture.** Point-in-time correctness (Week 2, "The Future Leaks In", and Week 4
Monday, "You Have Met This"). A training row may only use information that existed at
the moment the prediction would have been made.

**Run.** `make part2`

**You'll see.** One feature, for one restaurant on one date, and two numbers: what
your pipeline computed, and what was actually knowable at prediction time.

**What we are telling you.** The bug is in stage 3 (`rolling_aggs`). The failing
feature is `restaurant_prep_avg_30d`. The failing check is restaurant `R017` on
`2026-03-08`. The feature is **defined** as:

> For date D, the average prep time of that restaurant's deliveries over the 30 days
> **before** D, not including D. This is what the model could know when it predicts
> an order placed on D.

We are not telling you what the bug is.

**Change.** Stage 3 in `src/build_features.py`.

**Done when.** `make part2` passes. It checks the R017 value, and it checks that R208,
which had its first delivery on that date, has no value at all.

After your fix, some rows will have a NULL in this column. Decide whether that is a
bug before you try to fix it.

**Write.** What information leaked into the feature, and how would it have made the
offline error look better than production? Why are the NULLs you now see correct?

---

## Part 3 · Nothing errored

**Time:** about 60 minutes.

**Incident.** The orders team shipped a release on March 10. It was a reasonable
change and nobody told you about it. Your job ran that night and succeeded. Every
gate passed. The Sunday retrain used the data.

**From lecture.** Constraint 4: nothing errored. The check should live inside the
pipeline, between stages, as a gate, and a failed check needs a decision made in
advance.

**Run.** `make part3`

**You'll see.** The pipeline succeeds and the existing gate passes, and the test still
fails, because nothing caught what changed. Use `make peek DATE=2026-03-10` and
compare it to a normal day, such as `make peek DATE=2026-03-09`. Look at the **input
events** section of the output, not just the feature table. Finding what changed is
part of the task.

**Where gates run.** Gates run after stage 2 (`join_deliveries`), on that date's joined
deliveries, before anything is aggregated or written. That is the last point where a
bad day's data is still one day's data.

**Change.** `src/gates.py`. Two things:

1. **Add one gate** that catches this kind of change. Copy the pattern of the
   existing example gate.
2. **Choose a failure behavior for both gates**, the example one and yours, by
   setting `on_fail` to one of these:

| `on_fail` | What the runner does when the gate fires |
|---|---|
| `"fail"` | Stops the run with a non-zero exit. Nothing is written for that date. Yesterday's features keep being served |
| `"warn"` | Writes the partition anyway, records the warning in the run manifest, exits normally |
| `"quarantine"` | Writes the partition to `data/quarantine/` instead of `data/aggs/`, records it in the manifest, exits normally. Training never sees it |

The runner already implements all three. You only choose.

**Done when.** `make part3` passes, which checks all of these:

- Your gate fires on March 10.
- Every gate stays quiet on the first days of the data, when there is little or no
  history to compare against, and on the 30 days before the change. The test says
  which dates it runs. A gate that fires on normal days will be ignored by the
  people it pages, so false alarms fail the test.
- No gate raises an exception on any of those dates.
- Both gates have an `on_fail` value.

What happens on March 10 after your gate fires depends on the `on_fail` you chose.
The test prints it. Then look with `make peek DATE=2026-03-10` and `ls data/`.

At grading, we also run your gate against a **variant you have not seen**: a
different numeric input column, changed by a different factor, possibly in the other
direction. A threshold tuned to exactly this data will fail it. Build the gate you
would trust on a night you are not watching.

**Write.** What changed in the data, and why did the example gate miss it? For each
gate, which `on_fail` did you choose, and what reads the feature table downstream
that made you choose it? Who gets woken up by your choice, and who doesn't? Does your
gate compare against a trailing window or a fixed reference, and what would happen to
it a week after the change?

---

## Part 4 · Yesterday was wrong

**Time:** about 60 minutes.

**Incident.** A bug in the feature job shipped on March 5 and was fixed on March 12.
The fix is deployed, but the wrong values are still on disk, and the weekly retrain
ran twice while the bug was live. You need to know exactly what to repair, and which
models learned from bad data.

**From lecture.** Constraint 3: yesterday was wrong. Your tools version the pipeline;
you have to version the data it produced. A backfill is the normal pipeline pointed at
old dates, and it is only safe because of Part 1.

**Run.** `make part4`

This loads a recorded history into your data folder:

- `data/runs/*.json`: one run manifest per pipeline run, including every re-run.
  Each one records the run ID, git SHA, when it ran, which partitions it read, and
  which it wrote.
- `data/models/registry.json`: every model version, when it was trained, and the run
  ID of every partition it read.
- `data/incident.json`: the git SHA of the bad commit.

**Do Part 1 first.** This part runs a backfill, and a backfill is only safe if a re-run
is safe.

**Change.** No pipeline code. You write two SQL queries, saved at these exact paths.
Inside `make sql`, and when the test runs your files, three views exist: `runs`
(every manifest as one row), `models` (the registry), and `incident`. `outputs_written`
and `inputs_read` are list columns; `unnest()` turns them into rows.

1. **`queries/partition_status.sql`**: one row per date in the history, with columns
   `dt`, `run_id`, `git_sha`, and `status`. `run_id` and `git_sha` come from the
   **most recent** run that wrote that date. `status` is `'bad'` if that run was the
   bad commit and `'ok'` otherwise.
2. **`queries/contaminated_models.sql`**: one row per model version that read at
   least one partition written by the bad commit, with columns `model_version` and
   `bad_partitions` (how many it read).

Your queries must take the bad SHA from the `incident` view (or `data/incident.json`),
not have it typed in. A failed run wrote nothing, so it does not own anything.

Work it out by hand first:

1. `make sql` opens a DuckDB prompt with those views ready. Start with
   `SELECT * FROM runs LIMIT 3;` and `SELECT * FROM models;`.
2. Develop the two queries. `make sql FILE=queries/partition_status.sql` runs one
   file and prints the result.
3. Use the first query to decide which dates need repair. The answer is not simply
   "March 5 through March 11". Read the manifests.
4. Repair them yourself: `python -m src.runner --backfill <START> <END>`, more than
   once if the bad dates are not contiguous. Then run both queries again and look at
   what changed and what did not.

**Done when.** `make part4` passes. It loads the history fresh, runs your queries,
checks their shape, then repairs the table by backfilling exactly the dates **your**
query marks bad and runs them again. It runs that repair backfill twice on purpose: a
backfill is a re-run, and if Part 1 is not fixed the second pass doubles every repaired
partition.

**What that test does not tell you.** It checks that your queries run, that
`partition_status` has one row per date that was ever published, that the dates you
call bad were at least touched by the bad commit, and that your own answer still holds
after you repair it. It does **not** tell you whether those are the right dates. Nobody
in the incident gets told that either. Whether the answer is right is decided at
grading, against this history and against an incident you have not seen, so convince
yourself from the manifests before you submit.

At grading, your queries are run against this history **and** a different incident
history, with a different bad commit and different dates, and both results are checked
against the correct answer. Queries that hard-code this incident's dates or SHA fail
both.

**Write.** Which partitions were bad, which did you repair, and how do you know? After
your backfill, `partition_status` should be all `'ok'`, but `contaminated_models` has
not changed. Why not? What would you have to do about those models, and what would it
cost?

---

## Part 5 · Two questions, no code

**Time:** about 20 minutes. Answer both in your writeup, a paragraph each.

1. **The job dies at partition 31.** A backfill over 40 dates writes one partition at
   a time. It is killed after writing 30. What state is the feature table in, and what
   would a model that trained at 3am have learned from? What would you change about
   how partitions are written so a reader can never be fooled by a half-finished
   run? (Lecture: "The Job Dies at Partition 31" and "What That Forces".)
2. **The next incident.** Name one failure this pipeline is still vulnerable to after
   your fixes, and the check that would catch it. Why that check rather than another?

---

## What you submit

Two files, uploaded to Canvas.

**1. `submission.zip`**, built by `make submit`. It contains your code and leaves out
the generated data. Do not zip the folder by hand; the data folder is large and the
grader does not need it.

**2. One PDF** with your writeup and your AI use log, in this order:

- **Writeup:** one section per part (0 through 5), answering each **Write** prompt.
  A few sentences per prompt is enough. Two to three pages total.
- **AI use log:** see below.
- **Hints:** if you opened `HINT.md`, say which hints you read.

### AI use log (about one page)

This assignment is **Scenario 4, Open GenAI with Accountability.** Use AI tools
freely. You are responsible for understanding and explaining everything you submit.

**How much you use AI is not graded and does not affect your score.** The log is
graded only on whether it is complete. Honest reporting is the only thing that
matters here.

Your log has three parts:

1. **A table.** One row per meaningful use: what you asked for, which tool and model,
   what you kept, changed, or threw away, and how you checked it was right.
2. **Comments in your code.** Any AI-generated code you kept gets a short comment
   where it is used, for example `# AI-assisted: first draft of the gate, threshold
   is mine`.
3. **One time the AI was wrong.** What it told you, why it was wrong, and how you
   caught it. On this assignment you will very likely find one: pipeline code
   suggested by AI tools often has exactly the problems you are fixing.

Once you're working in industry - no one will care that you used AI to complete your work.
But "AI Said So" is not a defense of bad code or a harsh code review. You need to understand the 
work before you can delegate it to AI. My recommendation is to spend time working this by hand,
and using AI as a "guide" for you when you're stuck. Handing this assignment to AI will not help you
learn, and will get some of these wrong (I've checked).

### Hints

`HINT.md` has one hint per part. **Opening it costs nothing.** Just say in your
writeup which hints you read. Use it when you have been stuck for more than 30
minutes on the same thing.

---

## Grading

| Component | Points |
|---|---|
| Part 1 tests | 10 |
| Part 2 test | 10 |
| Part 3 tests, including the unseen variant | 10 |
| Part 4 tests, including the unseen history | 10 |
| Writeup, Parts 0 to 5 | 35 |
| Code review: fixes are small, readable, and fix the cause rather than cleaning up after it | 20 |
| AI use log, complete or not | 5 |
| **Total** | **100** |

Parts 1 and 2, and the visible checks for 3 and 4, run on your machine exactly as they
run for the grader. Two things are decided only at grading: your Part 3 gate against an
unseen variant, and whether your Part 4 answers are right.

---

## Time budget

| | Minutes |
|---|---|
| Part 0: setup, predictions, reading | 60 |
| Part 1: it ran twice | 30 |
| Part 2: it knew the future | 45 |
| Part 3: nothing errored | 60 |
| Part 4: yesterday was wrong | 60 |
| Part 5: two questions | 20 |
| Writeup and AI log | 45 |
| **Total** | **about 5.5 hours** |

If you have spent more than an hour stuck on setup, stop and send me the output of
`make doctor`. If you have spent more than 30 minutes stuck on one part, open
`HINT.md`.

---

## Late work

The course late policy applies: you have 5 late days for the semester, used in whole
days. If you use any on this assignment, email me after you submit and say how many.
