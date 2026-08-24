# CS 459 — Environment Setup

Note: Some of these instructions are AI-Generated (I don't have a Windows machine). If commands don't work, let's work through it together. 

**Try to start this before class Wednesday, Aug 26. At least download the prerequisites, please.** We'll use class time to
unstick whoever is stuck.

By the end you'll have a Python environment on your laptop, a separate Python
environment inside a container, and a notebook in the first one talking over
HTTP to a server in the second.
---

## Step 1 — git

**macOS.** Run `git --version` in Terminal. If it's missing, macOS offers to
install the Command Line Tools. Accept.

**Windows.** [git-scm.com/download/win](https://git-scm.com/download/win). Accept
the defaults; when asked about PATH, keep **"Git from the command line and also
from 3rd-party software."**

**Linux.** `sudo apt install git`, or your distro's equivalent.

**Everyone — set your identity once:**

```bash
git config --global user.name "Your Name"
git config --global user.email "you@u.boisestate.edu"
```

Commits record whoever these say you are.
---

## Step 2 — uv

`uv` manages Python versions and packages. One tool, one command, and it will
install the right Python for you if you don't have one — which is why we're
using it instead of hand-rolling `venv` and `pip`.

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then **close and reopen your terminal** (the installer edits your PATH, and
already-open shells don't see the change) and confirm:

```bash
uv --version
```

---

## Step 3 — Get the repo and build the environment

```bash
git clone https://github.com/BoiseState/CS459
cd setup
uv sync
```

That's the whole step. `uv sync` reads `pyproject.toml`, downloads a suitable
Python if needed, creates a `.venv` folder, and installs everything — usually in
a few seconds.

**You do not need to "activate" anything.** Prefix commands with `uv run` and it
uses the right environment automatically:

```bash
uv run jupyter lab
```

If you're used to `source .venv/bin/activate`, that still works and you can keep
doing it. `uv run` just removes the step you'd otherwise forget.

---

## Step 4 — A container runtime

You need something that can build and run containers. **Docker Desktop is the
path I'll support in office hours**.

Download: [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)

**macOS** — pick the right build, **Apple Silicon** (M-series) or **Intel**.
Apple menu → About This Mac if you're unsure. The wrong one fails confusingly
rather than clearly.

**Windows** — Docker Desktop needs **WSL 2**. The installer usually sets it up.
If it complains, open PowerShell **as Administrator**:

```powershell
wsl --install
```

Then reboot. Actually reboot — WSL isn't finished installing until you do, and
Docker will keep failing with an unhelpful message.

Some machines also need virtualization enabled in BIOS/UEFI ("Intel VT-x,"
"AMD-V," or "SVM Mode"). Symptom: Docker starts, then immediately reports the
virtual machine can't start. **If you hit this and aren't comfortable in your
BIOS, come see me — don't guess at BIOS settings.**

**Linux** — you want [Docker Engine](https://docs.docker.com/engine/install/),
not Docker Desktop. Do the post-install step that adds you to the `docker` group,
or you'll need `sudo` for every command.

**Verify — both of these must work:**

```bash
docker run hello-world
docker compose version
```

If `hello-world` prints a wall of text ending in "This message shows that your
installation appears to be working correctly," you're set.

> **Whatever you installed has to be *running*, not just installed.** With Docker
> Desktop that's the whale icon in your menu bar or system tray. "Cannot connect
> to the Docker daemon" always means the same thing: it isn't running. Docker
> Desktop doesn't launch at login unless you tell it to.

---

## Step 5 — Run the container

From this folder:

```bash
docker compose up --build
```

First build takes a minute or two — it's downloading the Python base image.
After that it's seconds. You'll know it worked when you see:

```
cs459-hello  | Serving on http://0.0.0.0:8000
```

**Leave this terminal open.** The service runs as long as that command does;
`Ctrl-C` stops it.

Check it in your browser: **[http://localhost:8000](http://localhost:8000)**
should return JSON.

---

## Step 6 — Run the notebook

Open a **second** terminal — the first one is busy — and from this folder:

```bash
uv run jupyter lab
```

Open `setup_check.ipynb`, fill in your name at the top, and run every cell in
order. There's one short written question near the end.

---

## Step 7 — Submit

With every cell run and the question answered:

**File → Save**, then **File → Export Notebook As → HTML**. Upload the `.html`
to Canvas.

Export *after* running everything, or your outputs won't be in the file and it
will look like you ran nothing.

---

## Troubleshooting

**`uv: command not found`**
Close and reopen your terminal. The installer changed your PATH and open shells
don't pick that up.

**`docker: command not found`**
Not installed, or not on PATH. On Windows, reopen your terminal after installing.

**`Cannot connect to the Docker daemon`**
Installed but not running. Start Docker Desktop (or `colima start`), wait for it
to settle, try again.

**`port is already allocated` / `address already in use`**
Something else owns port 8000. Edit `compose.yaml` and change the **left** number
only:

```yaml
ports:
  - "8080:8000"    # host 8080 -> container 8000
```

Then set `SERVICE_PORT = 8080` in the notebook's first code cell.

**Jupyter is using the wrong Python**
The notebook prints `sys.executable`. It should point inside this folder's
`.venv`. If it points at `/usr/bin/python3`, `C:\Python312\`, or Anaconda,
register the right kernel:

```bash
uv run python -m ipykernel install --user --name cs459 --display-name "Python 3 (cs459)"
```

Then in JupyterLab: **Kernel → Change Kernel → Python 3 (cs459)** and re-run from
the top.

**Notebook can't reach `localhost:8000`**
Walk the checklist the error message prints, in order. Nine times out of ten
`docker compose up` isn't running in the other terminal, or that terminal got
closed.

**The notebook says the service isn't in a container**
You started `app.py` directly instead of through Docker. Stop it and use
`docker compose up --build`.

**Build fails partway through a download**
Campus wifi. Re-run it — Docker caches finished layers and picks up roughly where
it left off.

**Something else**
Post in the course channel with your OS, the exact command, and the full error
text. "It doesn't work" isn't something I can debug.

---

## Docker commands worth knowing

```bash
docker compose up --build     # build and start
docker compose up -d          # start in background
docker compose ps             # what's running?
docker compose logs -f        # follow logs
docker compose down           # stop and remove

docker ps                     # running containers
docker images                 # local images
docker exec -it cs459-hello /bin/bash   # get a shell INSIDE the container
docker system prune           # reclaim disk from stopped containers/unused images
```

Try that `docker exec` one now, while the container is up. It drops you inside.
Run `ls`, `python --version`, `whoami`, `cat /etc/os-release`. You're in a
different filesystem running a different Linux than your laptop. `exit` gets you
out.
