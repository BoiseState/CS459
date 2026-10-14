# CS 459 · Assignment 3: Deployment Patterns

You are joining the revenue team at a hotel group. A model flags bookings that are likely
to cancel, and the hotels use those flags to ask for deposits and to overbook. The person
who built it left. Your job is to get a better model into production without breaking
anything, using the team's MLflow server as the record of everything you do.

The full instructions are in **SPEC.md**. This file only gets you running.

## Setup (do this first)

From this folder, on your laptop:

```bash
docker compose build
docker compose up -d mlflow          # the team's MLflow server
docker compose run --rm app          # your shell; the prompt becomes  a3 $
```

Inside the container:

```bash
make doctor                          # must end with: all checks passed
make bootstrap                       # loads the team's history (about 2 minutes)
```

Then open **http://localhost:5050** in your browser. That's the MLflow UI. You should see
an experiment called `hotel-cancellations` and a registered model called `cancellations`.

If `make doctor` fails and you've been stuck for more than an hour, email me its full output.

## Day to day

| Command | What it does |
|---|---|
| `docker compose up -d mlflow` | Start the MLflow server (it keeps running in the background) |
| `docker compose run --rm app` | Open your shell |
| `make test` or `make test1` ... `make test5` | Visible tests, all or one part |
| `make drill` | Replay the Part 5 incident |
| `make submit` | Build `submission.zip` |
| `make backup` | Copy your MLflow data to `backups/` in your repo folder. Do this at the end of every session |
| `make submit` | Build `submission.zip` |

## Pausing and resuming

**Stopping for the day:**

```bash
make backup                  # inside the container
exit                         # leave the container
docker compose stop          # stop the MLflow server
```

**Picking back up:**

```bash
docker compose up -d mlflow
docker compose run --rm app
```

Your runs, models and aliases are all still there. They live in a Docker volume called
`a3-deployment_mlflow-data`, not in your repo folder, so you won't see them in Finder or
Explorer. Inside the container they're at `/work/mlflow_data`.

**Never run these** while you're working on this assignment. Each one deletes that volume,
and with it every run you've logged:

- `docker compose down -v` (plain `docker compose down` is fine)
- `docker volume prune --all`, or `docker system prune --volumes`
- Docker Desktop's **Clean / Purge data** or **Reset to factory defaults**

A note on `docker volume prune`: without `--all`, current versions of Docker only remove
volumes that have no name, so this one is left alone. With `--all`, it removes every named
volume that no container is using. That's one more reason to stop with `docker compose stop`
rather than `docker compose down`: `stop` keeps the containers, so the volume stays in use.

If your run IDs disappear, any you've cited in your writeup no longer exist in your
submission, and the grader checks.

**If you lose your MLflow data anyway**, restore your latest backup. From your repo folder:

```bash
docker compose stop mlflow
docker compose run --rm --no-deps app make restore FILE=backups/<the newest file>.zip
docker compose up -d mlflow
```

## Files

| Path | Yours to change? |
|---|---|
| `src/train.py`, `src/evaluate.py`, `src/gate.py`, `src/register.py`, `src/shadow.py`, `src/serve.py` | Yes |
| `answers/` | Yes |
| `config/serve.yaml` | Yes |
| Everything else | No. The grader replaces it with its own copy |
