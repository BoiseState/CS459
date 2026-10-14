# Hints

Opening these is free. Say in your writeup which ones you read. Try for 30 minutes first.

How to use MLflow isn't a hint; it's in SPEC.md under **MLflow basics**.

<details><summary>Part 1: my rebuild doesn't match</summary>

Gradient boosting holds out part of the training data for early stopping, chosen at random.
Without a fixed `random_state`, two fits on identical data differ. Check also that the
training period you logged is the one you actually used, and that every classifier
parameter is logged (`get_params()` returns them all as a dict).
</details>

<details><summary>Part 2: how do I tell the runs apart?</summary>

Put all five side by side in the UI (select them, then Compare) and look at the parameters,
not the metric. Three things to check for each: what it was trained on, how the data was
split, and what it was scored on. Then check `features.py` for which columns are known at
booking time.
</details>

<details><summary>Part 2: which models are usable?</summary>

A model is usable if it never saw holdout bookings while training and only uses inputs
available at booking time. A run can fail the comparison for a reason that has nothing
to do with its model.
</details>

<details><summary>Part 3: how should register.py be structured?</summary>

One short function per step reads well and is easy to test. The seven steps in the file's
docstring map onto the registry calls in SPEC.md: `register_model` for step 1,
`set_model_version_tag` for steps 2 and 6, `get_model_version_by_alias` to find the
champion's version, `search_runs` for step 3, `get_run` for step 4, and
`set_registered_model_alias` for step 7.
</details>

<details><summary>Part 3: finding the champion's evidence</summary>

Your Part 2 evaluation of the champion is a run tagged `a3.part = 2` and
`evaluates_version = <the champion's version>`. Search for it, newest first. If you
evaluated it more than once, use the newest. If there isn't one, stop with a clear message
rather than gating against nothing.
</details>

<details><summary>Part 3: the gate gets the wrong metrics</summary>

A run's metrics come back as one dict with every period in it. The gate wants the holdout
ones: keep the keys that start with `holdout.`. Parameters come back as strings, so the
threshold is `"0.55"`, not `0.55`.
</details>

<details><summary>Part 5: where do I start?</summary>

Make the service tell you which model version answered before you change anything else.
Then rerun the drill and believe what it shows you.
</details>

<details><summary>Part 5: the version is right now, but the flags still look wrong</summary>

A model release is more than the model file. List everything that changed during the
10:02 release, and check which of those things the 10:14 rollback put back.
</details>
