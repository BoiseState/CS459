# Assignment 3 Rubric (100 points)

## Tests (40)

The grader starts your MLflow data from `submission.zip`, puts back the provided files,
and runs these checks. Each is all or nothing.

| Part | Points | Checked |
|---|---|---|
| 1 | 2 | Required params, a non-None `random_state`, fingerprint matches the data file |
| 1 | 2 | Model signature recorded; the four plots; validation and holdout metrics, including every group |
| 1 | 6 | **Rebuilt from your logged params alone, it reproduces your `holdout.roc_auc`** |
| 2 | 5 | One point per correct verdict and reason in `answers/part2.yaml` |
| 2 | 1 | Champion evaluated at 0.65 with the full holdout metrics |
| 2 | 2 | Every history model that can be fairly scored, scored |
| 3 | 8 | Your `should_promote` on eight unseen cases (limits, small segments, missing and non-finite values) |
| 3 | 4 | Registry: version 1 tagged 0.65; your challenger's threshold, `gate.passed` and `gate.reasons` tags, and `gate.passed` agrees with the policy applied to your logged metrics |
| 4 | 4 | Your shadow report matches a rescore: disagreement overall and by group, flag rates, the labeled subset; logged as a run |
| 5 | 6 | The service reports its version, follows `@champion` without a restart in both directions, takes its threshold from the version, and refuses a version it can't serve safely |

## Writeup (35)

| Part | Points | Full credit |
|---|---|---|
| 0 | 4 | Names the champion's version and run; a specific list of what can't be known from its record; a concrete cost of that gap during an incident |
| 1 | 5 | Sources of rebuild drift are real ones, each matched to what was logged; the PR-curve comparison is explained; the feature question is reasoned, not guessed |
| 2 | 6 | Each verdict explained with the evidence that shows it (which parameter, which value); rescored numbers compared with what was originally logged |
| 3 | 7 | Threshold tradeoff stated in the hotels' terms; a believable case for rule 4; the per-1,000 translation is correct for your numbers |
| 4 | 5 | Where they disagree, what the known outcomes show, and a clear limit on what about a third of the outcomes can tell you |
| 5 | 5 | Each cause, the evidence for it, and a prevention that would actually have caught it; a realistic account of what following the alias costs |
| 6 | 3 | A clear decision a non-ML reader could act on, backed by cited run IDs and numbers |

Run IDs cited in the writeup are checked against your submission. A run ID that isn't
in your MLflow loses the points for the claim it supports.

## Code review (20)

| Points | Looking for |
|---|---|
| 6 | Part 1 logging is complete and readable, not a dump of everything in scope |
| 5 | The gate reads like the policy: one clear check per rule, reasons that say what failed |
| 5 | The service fix addresses the causes, not the drill: it would still work for a version the drill never uses |
| 4 | No hard-coded run IDs, versions, or numbers that should come from MLflow |

## AI use log (5)

Complete or not: the table, comments where generated code was kept, and one documented
case where the AI was wrong.
