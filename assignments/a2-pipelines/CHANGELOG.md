# Changelog

Fixes to the starter land on `master`. Run `git pull` before every work session.

## 2026-09-22

- **Fixed: the repo would not check out on Windows.** Run manifest filenames contained
  `:`, which Windows does not allow in a filename, so the clone failed on those files
  and left them missing. The 45 files under `tests/fixtures/part4/runs/` are renamed,
  and `src/runner.py` now writes new manifests the same way:
  `2026-03-08T02-00-04Z-a1b2.json` rather than `2026-03-08T02:00:04Z-a1b2.json`.
  Nothing else changed, and nothing reads a run id as a date, so this is a rename only.

## 2026-09-18

- Initial release.
