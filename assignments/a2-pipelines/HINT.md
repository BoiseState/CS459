# Hints

Opening this file costs nothing. Say in your writeup which hints you read. Use a hint
after you have been stuck for 30 minutes on the same thing, not before.

Each hint says where to look and what question to ask. None of them says what to type.

---

## Part 1 · It ran twice

The write happens in one statement in stage 4. Read every option on that statement,
then read the DuckDB documentation page on partitioned writes and compare the options
it lists. The engine offers more than one way to write into a folder that already
exists, and they do different things to the *other* dates in the folder. Part 1's
second check exists because one of them looks right on a single date and destroys
the rest of the table.

If the first check passes and you got there by removing rows after they were written,
you have not fixed it. The job still writes twice. Ask instead: what would make a
second write land in exactly the same place as the first, and replace it?

## Part 2 · It knew the future

Stage 3 has one `WINDOW` clause and every feature uses it. The definition of the
feature in the spec says which days belong in the window. Write those days down as
"D minus something to D minus something", then read the frame clause and ask whether
the days it includes are the same list. Look hardest at the upper edge.

Once the oracle passes, look at R208's row. If you are tempted to fix the NULL, first
answer: what number could possibly go there, and where would it have come from?

## Part 3 · Nothing errored

Run `make peek DATE=2026-03-10` and `make peek DATE=2026-03-09` side by side and
read the input events table, one row per column. One column moved. Now ask why the
example gate, which counts rows, could never have seen it.

For the gate itself: you do not know which column the upstream team will change
next, or in which direction. A gate that checks one named column against one
hand-picked number is a gate for the incident you already had. Compare a summary
statistic of *each* numeric column today against the same statistic on the days
before, and decide how far apart is too far. The `joined` view already contains
the earlier days.

The first days of the data have no history. Decide what your gate returns then,
and make sure it is not an exception.

## Part 4 · Yesterday was wrong

Start in `make sql`. `SELECT * FROM runs LIMIT 3;` and `SELECT * FROM models;` show
you the shapes. `outputs_written` and `inputs_read` are lists; `unnest()` turns a
list into rows (there is an example in `examples/duckdb_basics.py`).

For `partition_status`: one date can have several runs. Some failed and wrote
nothing. One was written again later. "The run that owns a partition" is the most
recent one that successfully wrote it, so sort by `finished_at` and keep one row
per date. `row_number() OVER (PARTITION BY ... ORDER BY ...)` is the usual tool.

For `contaminated_models`: the registry does not record which commit a model was
trained on. It records which *run* wrote each partition it read. Join that run ID
back to the manifests and the commit is right there.

If your bad-date list is exactly March 5 through March 11, look again at the runs
for March 2 and March 9.
