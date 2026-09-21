# CS 459 · Assignment 2: Pipelines

A nightly feature pipeline that works, passes its happy-path test, and is wrong in
four ways you cannot see by reading it. Your job is to find and fix them.

**The assignment itself is in [`SPEC.md`](SPEC.md).** This page only gets you set up.

---

## What you need

- **Docker Desktop**, running.
- **Git.**
- A code editor.

You do **not** need Python, DuckDB, or anything else installed on your machine.
Everything runs inside the container.

---

## Setup (about 10 minutes)

On your own machine, in a terminal:

```
git clone <class repo URL>
cd <the class repo>/assignments/a2-pipelines
docker compose build
docker compose run --rm app
```

The first build takes a few minutes. The last command opens the **pipeline shell**,
a terminal inside the container. Your prompt changes to:

```
pipeline $
```

Inside the pipeline shell, run:

```
make doctor
make data
make test
```

`make doctor` should end with `all checks passed`. If it does not, stop and send me
its full output. `make test` will show failures. That is expected; it is where the
assignment starts.

---

## How to work

**Every command in `SPEC.md` is typed inside the pipeline shell.** To get back into it
later, run `docker compose run --rm app` from this assignment's folder. To leave it,
type `exit`.

**Git lives above this folder.** The class repo's `.git` is a few levels up and the
container only sees this folder, so run manifests written inside the pipeline shell
record `git_sha` as `unknown`. That is expected and nothing depends on it.

**Edit code on your own machine**, in your normal editor. The pipeline shell sees your
changes immediately. There is nothing to rebuild.

**Your data is not in your repo folder.** The pipeline writes to a Docker volume, so
you will not see a `data/` folder in Finder or File Explorer. This keeps every file
operation identical on Mac, Windows, and Linux. To look at data, use `make peek`,
`make sql`, or `ls data/` from inside the pipeline shell.

---

## Commands

All of these run inside the pipeline shell.

| Command | What it does |
|---|---|
| `make doctor` | Checks your environment. Send me this output if anything is broken |
| `make data` | Generates the synthetic order and delivery events |
| `make test` | Runs every part and prints a summary (about a minute) |
| `make part0` ... `make part4` | Runs one part, starting from clean data |
| `make peek DATE=2026-03-08` | Summary statistics for one date: the input events and the feature table |
| `make sql` | Opens a DuckDB prompt with the data ready to query as views |
| `make sql FILE=queries/x.sql` | Runs one SQL file against those views and prints the result |
| `make reset` | Deletes all generated data. Run `make data` afterward |
| `make submit` | Builds `submission.zip` in your repo folder, ready for Canvas |

The pipeline itself runs as `python -m src.runner`. For example:

```
python -m src.runner --date 2026-03-03
python -m src.runner --backfill 2026-03-01 2026-03-21
```

---

## Before every session

```
git pull
```

If anything in the repo is fixed after release, the fix lands on `main` and is listed
in `CHANGELOG.md`. Pulling first means you never spend an hour on a problem that has
already been fixed. If `git pull` refuses because you have local changes, copy your
edited files somewhere safe, pull, and put them back. Email me if that looks scary.

---

## Getting help

- **Setup problems:** send me the output of `make doctor`.
- **Stuck on a part for more than 30 minutes:** open `HINT.md`. It is free; just say
  so in your writeup.
- **Something looks like a bug in the repo:** email me with the command you ran and
  what it printed.
