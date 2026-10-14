# Assignment 3: Deployment Patterns

**Due:** Monday, October 26, 11:59pm Mountain
**Expected effort:** 6 to 8 hours
**AI use:** Scenario 4, Open GenAI with Accountability

## What you'll learn

By the end of this assignment you should be able to:

1. Use MLflow to track experiments: runs, parameters, metrics, artifacts, and a model with its input schema.
2. Record enough about a training run that someone else could rebuild the model.
3. Inherit someone else's model and code, and work out what you can and can't trust from the record they left.
4. Compare experiments fairly: spot leakage, mismatched splits, and numbers measured on different data.
5. Turn a business rule into a promotion gate in code, run on logged evidence.
6. Release a model through a registry, with versions and aliases.
7. Shadow a model before release, and reason about outcomes that arrive late.
8. Roll back, and understand that a release is more than the model file.
9. Explain a promote-or-hold decision to someone who isn't an ML person.

## The situation

The hotel group's revenue team uses a model to flag bookings that are likely to cancel.
A flagged booking gets a deposit request, and the hotel may overbook against it. Both
decisions cost money when the flag is wrong: a guest who was going to show up gets
hassled for a deposit, or worse, arrives to a full hotel and has to be sent somewhere
else. The hotels have been clear about this: **a flag has to be right at least 80% of
the time.**

The model in production is a logistic regression. It runs at a threshold of **0.65**: a
booking is flagged when the model's cancellation probability is 0.65 or higher. The
team set it that high after the hotels complained about walked guests last summer.

The person who built it left. The team's MLflow server has everything that was ever
recorded about it, which turns out not to be much. Your job is to find out what you
inherited, build a better model that you could defend, decide whether to ship it, and
make sure that if it goes wrong, undoing it works.

### When this is set

The data runs from 2015 to August 2017, so the story is set in **spring 2017**. The team's
past runs are dated to match: the champion was trained in January 2017, and the five
experiments after it are named for the day each was run (`hgb-0130` is January 30, 2017,
then weekly). Your own runs will show today's date. That's expected.

### The data

`data/hotels.csv` has 119,390 real bookings at two hotels, a city hotel and a resort,
with arrivals from July 2015 to August 2017. `is_canceled` is the outcome. `src/features.py`
defines the features (all known when the booking is made) and four periods, by arrival date:

| Period | Arrivals | Use it for |
|---|---|---|
| `train` | Jul 2015 to Jun 2016 | Fitting |
| `validation` | Jul 2016 to Dec 2016 | Choosing anything: settings, threshold |
| `holdout` | Jan 2017 to Mar 2017 | Judging the final model, and comparing it to the champion |
| `next_quarter` | Apr 2017 to Jun 2017 | Shadow traffic (Part 4) |

### The models

The **champion** is a logistic regression: the categorical features one-hot encoded, the
numeric ones scaled. It's a common first production model: quick to train, stable, and
easy to explain.

Every experiment since, and the model you'll train, is a **gradient boosted tree model**
(`HistGradientBoostingClassifier`). Trees can pick up interactions the logistic regression
can't, like a long lead time mattering more for some deposit types than others. Two
things to know about it:

- **It has randomness in it.** With this much data it sets aside a random 10% of the
  training rows to decide when to stop adding trees. Unless you fix `random_state`, two
  fits on identical data come out slightly different. That matters in Part 1.
- **Its probabilities aren't on the same scale as the logistic regression's.** A score of
  0.6 from one model doesn't mean the same thing as 0.6 from the other. That's why each
  model gets its own threshold, chosen for that model.

---

## MLflow basics

You haven't used MLflow before, so here's what you need. Nothing in this assignment
depends on knowing more than this section.

### The pieces

| Term | What it is |
|---|---|
| **Experiment** | A named collection of runs. Ours is `hotel-cancellations` |
| **Run** | One execution of training or evaluation code. Has a 32-character ID |
| **Parameter** | A setting you record once per run. Always stored as text |
| **Metric** | A number you measured |
| **Tag** | A label on a run or a model version. We use `a3.part` to mark which part a run belongs to |
| **Artifact** | A file stored with a run: a plot, or the model itself |
| **Registered model** | A named model, `cancellations`, with numbered **versions** |
| **Version** | One registered copy of some run's model. Versions have their own tags |
| **Alias** | A movable name for one version. `@champion` is what the hotels use; `@challenger` is what you propose. Moving an alias is how this team ships and rolls back |

### The UI (http://localhost:5050)

Labels can differ slightly between MLflow versions, but the layout is:

- **Experiments → `hotel-cancellations`** lists every run. Click a run to see its
  parameters, metrics and tags, and its **Artifacts** (files, including the model).
- **Comparing runs:** tick several runs in the list and choose **Compare** to see their
  parameters and metrics side by side.
- **Models → `cancellations`** lists the versions and their aliases. A version's page
  shows its tags and links to the run that produced it.

### In code

These are the calls this assignment needs. The `MLFLOW_TRACKING_URI` environment variable
in the container already points everything at the team's server.

```python
import mlflow
from mlflow import MlflowClient
from tracking import log_model          # always use this to log a model (see below)

client = MlflowClient()

# Log a run
mlflow.set_experiment("hotel-cancellations")
with mlflow.start_run(run_name="my-run") as run:
    mlflow.set_tag("a3.part", "1")
    mlflow.log_param("threshold", 0.55)
    mlflow.log_params({"model.max_iter": 300, "model.learning_rate": 0.05})
    mlflow.log_metrics({"holdout.precision": 0.83, "holdout.recall": 0.56})
    mlflow.log_figure(fig, "plots/holdout_pr_curve.png")      # a matplotlib figure
    log_model(model, input_example=train[FEATURES].head(5))
    print(run.info.run_id)

# Read a run back
r = client.get_run(run_id)
r.data.params["threshold"]          # parameters come back as strings: "0.55"
r.data.metrics["holdout.precision"]
r.data.tags

# Find runs. Tag names with dots in them need backticks.
exp_id = client.get_experiment_by_name("hotel-cancellations").experiment_id
runs = client.search_runs([exp_id], "tags.`a3.part` = '2' and tags.evaluates_version = '1'",
                          order_by=["attributes.start_time DESC"])     # newest first

# Load a model
mlflow.sklearn.load_model(f"runs:/{run_id}/model")          # the model a run logged
mlflow.sklearn.load_model("models:/cancellations/1")         # a specific version
mlflow.sklearn.load_model("models:/cancellations@champion")  # whatever the alias points at

# The registry
mv = mlflow.register_model(f"runs:/{run_id}/model", "cancellations")   # creates a new version
mv = client.get_model_version_by_alias("cancellations", "champion")    # mv.version, mv.run_id, mv.tags
client.set_model_version_tag("cancellations", mv.version, "threshold", "0.65")
client.set_registered_model_alias("cancellations", "challenger", mv.version)
```

`register_model` may print a warning that the run "has no artifacts at artifact path
'model'" and that it's registering the logged model instead. That's harmless.

**Always log models with `tracking.log_model`**, never `mlflow.sklearn.log_model` directly.
MLflow's safe model format refuses to reload gradient boosting models unless they're
logged with a setting the helper takes care of.

**Tags with `a3.part`** mark the runs each part is graded on. Use them exactly as written.
If you log the same part more than once, the newest run counts.

### Protecting your work

Your runs, models and aliases live in a Docker volume, not in your repo folder. If that
volume is deleted, every run you've logged goes with it, along with any run IDs your
writeup cites.

- **At the end of every session**, run `make backup` inside the container. It saves a copy
  in `backups/` in your repo folder. Then `exit` and `docker compose stop`.
- **To pick back up:** `docker compose up -d mlflow`, then `docker compose run --rm app`.
- **Never run** `docker compose down -v`, `docker volume prune --all`, `docker system prune --volumes`,
  or Docker Desktop's **Clean / Purge data** or **Reset to factory defaults**. Each one deletes
  the volume. Plain `docker compose down` is fine.
- **If you lose it anyway**, the README ("Pausing and resuming") shows how to restore your
  latest backup.

---

## Part 0. What did you inherit? (writeup only)

Open the MLflow UI and find the champion: which version, which run produced it, and what
that run recorded.

**Writeup:**
1. What can you tell about how the champion was trained, and what can't you? Be specific.
   "Not much" is true but not an answer.
2. Suppose the champion started misbehaving tomorrow. What would the missing record cost
   you while you tried to work out why?

---

## Part 1. Make training rebuildable

`src/train.py` trains a gradient boosting model and logs one number. If that model went
to production and misbehaved, nobody could say what data it saw or how to build it again.

Change `train.py` so its run records everything needed to rebuild the model exactly, and
tag the run `a3.part = 1`.

**Choosing the threshold.** The team's rule: **the lowest threshold, in steps of 0.05 from
0.30 to 0.95, whose validation precision is at least 0.90.** The team targets 0.90 on
validation, above the hotels' 0.80, to leave room: precision falls when cancellations
become less common, and the holdout has fewer cancellations than validation.

The run must log:

**Parameters**

| Name | Value |
|---|---|
| `model.class` | `HistGradientBoostingClassifier` |
| `model.<name>` | Every parameter of the classifier, from `get_params()`, including `random_state` (not None) |
| `features` | The feature columns, comma-separated, in order |
| `period.train`, `period.validation`, `period.holdout`, `period.next_quarter` | `start..end`, e.g. `2015-07-01..2016-07-01` |
| `data.sha256`, `data.rows`, `data.first_arrival`, `data.last_arrival` | From `features.fingerprint()` |
| `code.version` | Something that changes when the training code changes. Say in your writeup what you used |
| `lib.sklearn`, `lib.mlflow`, `lib.python` | Library versions |
| `threshold` | Chosen by the rule above |

**Metrics:** everything `metrics.evaluate()` returns, for both the `validation` and the
`holdout` period, at your threshold.

**Plots**, as artifacts, for both periods. `metrics.py` draws them; you log them with
`mlflow.log_figure`:

| Artifact path | From |
|---|---|
| `plots/validation_pr_curve.png`, `plots/holdout_pr_curve.png` | `metrics.pr_curve_figure` |
| `plots/validation_confusion_matrix.png`, `plots/holdout_confusion_matrix.png` | `metrics.confusion_figure` |

**The model**, logged with `tracking.log_model` and an `input_example` of a few training
rows, so MLflow records its input schema.

**How it's checked:** the grader reads your run's parameters, rebuilds the model from them
alone, and must get your logged `holdout.roc_auc` back. If your record is incomplete,
the rebuild comes out different.

**Writeup:**
1. Even with identical code, what could make a rebuild come out different? For each thing
   you list, say what you logged that rules it out, or that would show it happened.
2. Look at your two PR curves. Where does your threshold sit on each, and why isn't it in
   the same place?
3. Two of the features are the average daily rate (`adr`, the average price per night) and
   the number of special requests. Are both really known at the moment a booking is made?
   Answer from how hotel bookings work; you can't settle it from the data.

---

## Part 2. Comparing experiments fairly

The team's history has five runs, `hgb-0130` through `hgb-0227`. Several log an `auc`
that beats the champion's. Before you build on any of them, you need to answer two
different questions about each one:

1. **Is its logged number comparable to the champion's?** Was it measured the same way,
   on the same kind of data? You answer this from the run's record alone.
2. **Is its model usable?** A model is usable if it never saw holdout bookings while
   training and only uses inputs available when a booking is made. If it's usable, you
   can score it yourself on the holdout and get a number that *is* comparable.

The answers can differ. A run can log a number you can't compare, for a reason that has
nothing to do with its model.

**Step 1.** For each of the five, fill in `answers/part2.yaml`: is its `auc` a fair
comparison with the champion's, and if not, why. The file lists the reasons to choose from.

**Step 2.** Write `src/evaluate.py` so that it scores an existing model on the holdout and
logs a new run with:

- tag `a3.part = 2`
- tag `evaluates_run = <the run whose model you scored>`, and for a registered version also
  `evaluates_version = <version number>`
- param `threshold`, and the `data.*` fingerprint params
- every metric from `metrics.evaluate(..., prefix="holdout")`

**Step 3.** Use it to evaluate:
1. **The champion**, version 1, at its real threshold of 0.65. Part 3 can't work without this.
2. **Every history run whose model is usable.** These runs never chose a threshold, so
   score them at 0.5 and compare them on `holdout.roc_auc`, which doesn't depend on one.

**Writeup:** for each run, the evidence behind your verdict (which parameter, which value),
and for each model you rescored, how its holdout numbers compare with what it originally logged.

---

## Part 3. A promotion gate

The hotels' rule (a flag must be right 80% of the time) has to be written down as code
that runs before anything is promoted, and the evidence it runs on has to be the evidence
recorded in MLflow.

**Choose a challenger.** Train the model you want to propose with your Part 1 code. You
may change its settings, but choose them using the validation period only. Its threshold
follows the rule in Part 1.

**Implement `should_promote(champion, challenger)` in `src/gate.py`.** Both arguments are
dicts of holdout metrics, named as `metrics.evaluate` names them. Return a `Decision` with
`promote` and, when it is False, a reason for every rule that failed. The policy:

1. **Precision floor.** The challenger's `holdout.precision`, `holdout.hotel.city.precision`
   and `holdout.hotel.resort.precision` must each be at least 0.80.
2. **It has to be better.** The challenger's `holdout.recall` must be at least 0.03 higher
   than the champion's.
3. **No segment left behind.** For every market segment (`segment.*`) where the champion's
   `holdout.<segment>.n` is at least 500, the challenger's precision may not be more than
   0.05 below the champion's.
4. **Missing evidence is a no.** If any metric a rule needs is missing, or isn't a finite
   number, don't promote.

Comparisons at exactly a limit pass. Use the `TOLERANCE` in `gate.py` so that floating point
doesn't decide a tie. The grader runs your function against cases you haven't seen.

**Write `src/register.py`** so that `python src/register.py --run-id <id>`:
1. registers that run's model as a new version of `cancellations`,
2. tags the new version `threshold = <the run's threshold param>`,
3. reads the champion's evidence: your Part 2 evaluation run for its version,
4. reads the challenger's holdout metrics from its own run,
5. runs your gate,
6. tags the new version `gate.passed` (`true` or `false`) and `gate.reasons`,
7. points `@challenger` at the new version. It must not move `@champion`.

**One more thing:** the champion's version has no `threshold` tag, because the threshold lived
in `config/serve.yaml`. Tag version 1 with `threshold = 0.65`. From here on, **a version's
`threshold` tag is the one source of truth for the threshold it runs at.** Anything that
serves a version reads it from there, and a version without one must not be served.

**Writeup:**
1. Your threshold and what it trades: what you give up by not going lower.
2. Rule 4 blocks promotion when a metric is missing, instead of skipping that check.
   Describe a situation where skipping it would have shipped something bad.
3. Translate your challenger into the hotels' terms: per 1,000 holdout bookings, how many more
   cancellations does it flag correctly than the champion, and how many more wrong flags does it make?

---

## Part 4. Shadow deployment

Before the hotels act on your model, run it next to the champion on traffic it hasn't
seen, and compare what the two would have decided.

Pretend today is **April 30, 2017**. The shadow traffic is every booking arriving April to
June 2017. For bookings that already arrived in April, you know whether they canceled. For
May and June arrivals, you don't yet: you only learn the outcome once the arrival date
passes. So on April 30 you can see both models' decisions for the whole quarter, but you
can only check who was right on the bookings that have already arrived.

`src/shadow.py` has the plumbing done: reading the data, scoring, writing the report and
logging the run. You write three functions:

- `load_by_alias`: load a model **by its alias**, with the threshold from its version's tag,
- `disagreement`: how often the two models decide differently, overall and for each group
  in `metrics.GROUPS`,
- `known_by`: which bookings have an outcome you'd know on the `as_of` date.

Then run `python src/shadow.py --as-of 2017-04-30`. It writes `answers/shadow.json` and logs
a run tagged `a3.part = 4`. The report's fields:

| Field | Meaning |
|---|---|
| `champion_version`, `challenger_version` | Version numbers, as strings |
| `as_of` | The date you passed |
| `n` | Bookings scored |
| `champion_flag_rate`, `challenger_flag_rate` | Share of bookings each one flags |
| `disagreement_rate` | Share of bookings where one flags and the other doesn't |
| `disagreement_by_group` | The same, for each group, keyed by its name |
| `labeled_fraction` | Share of the quarter's bookings whose outcome is known on `as_of` |
| `labeled` | Each model's precision and recall, on those bookings only |

When you're done, decide whether to promote. If you do, `make promote` moves `@champion`
to your challenger (it refuses if the gate didn't pass).

**Writeup:** where the two models disagree, what the bookings with known outcomes say about
which one is right, and how much you trust a judgment made on `labeled_fraction` of the data.

---

## Part 5. Rollback

Last quarter the team had the incident below. `make drill` replays it, using your
challenger as the new release. It needs Part 3 done first: a version with the `@challenger`
alias, and version 1 tagged with its threshold.

> **Incident report.** 10:02: the challenger was released per the deploy runbook. 10:09:
> the hotels report a lot more bookings flagged than usual. 10:14: ops rolled back by
> moving `@champion` to the previous version. 10:30: the hotels report nothing has changed.
> 10:45: ops restarted the service. Still nothing has changed.

Find out why, and fix it so that a rollback actually restores the old behavior. The
service is `src/serve.py`; how it is released is in `src/drill.py` and `config/serve.yaml`.
There is more than one cause.

When you're done:
- `Service()` must work with no arguments.
- Every prediction it returns must include `model_version`, the version that produced it,
  so the next incident starts with evidence.
- After `@champion` moves, the same running `Service` must answer like that version,
  without a restart.
- `make drill` should show the rollback working.

**Writeup:**
1. Each cause you found, the evidence that showed it, and what would have caught this
   before it reached the hotels.
2. How does your service find out that `@champion` moved? What does that cost on each
   request, and what happens if the MLflow server is unavailable? Would you design it
   differently if the service handled a thousand requests a second?

---

## Part 6. The recommendation (writeup only)

Write to the revenue lead, who is not an ML person. Promote or hold, and why. Cite your
run IDs and the numbers that matter. Say what you would watch in the first weeks after
release, given that most outcomes arrive late.

---

## What you may change

`src/train.py`, `src/evaluate.py`, `src/gate.py`, `src/register.py`, `src/shadow.py`,
`src/serve.py`, `answers/`, and `config/serve.yaml`. You may add new files in `src/`.

The grader replaces every other provided file with its own copy, and recreates the
history from `src/bootstrap.py`, so changes there won't count.

## What to submit

1. **`submission.zip`**, from `make submit` (it includes your MLflow data; don't zip by hand).
2. **One PDF**: your writeup for Parts 0 to 6, your AI use log, and which hints you opened.

Your writeup must cite run IDs from your own MLflow. The grader checks every one against
your submission. Run `make backup` at the end of every session, and see "Pausing and resuming" in
the README for what never to run.

## Grading

| Component | Points |
|---|---|
| Tests, Parts 1 to 5 | 40 |
| Writeup, Parts 0 to 6 | 35 |
| Code review | 20 |
| AI use log | 5 |

`RUBRIC.md` has the detail. The visible tests (`make test`) check the shape of your work.
The grader runs more: rebuilds your Part 1 model, checks your Part 2 answers, tries your
gate on cases you haven't seen, rescores your shadow report, and rolls back your service
in ways the drill doesn't.

## AI use

Scenario 4, as in Assignment 2. Use AI tools freely; you are responsible for everything
you submit. The log is graded on completeness, not on how much you used AI: a table of what
you asked for and what you did with it, a comment in your code wherever you kept generated
code, and one case where the AI was wrong and how you caught it.

## Getting unstuck

`HINT.md` is free to open; say in your writeup which hints you read. Run `git pull` before
each work session. Setup problems: email me the output of `make doctor`.
