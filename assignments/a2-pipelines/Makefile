# Every target runs inside the pipeline shell (docker compose run --rm app).
# Outside the container it falls back to `uv run`, which works if you have uv installed.

ifdef IN_PIPELINE_CONTAINER
PY := python
else
PY := uv run python
endif

DATE ?=
FILE ?=

.PHONY: doctor data test part0 part1 part2 part3 part4 peek sql reset submit

doctor:   ; $(PY) -m tools.doctor
data:     ; $(PY) -m src.generate_events
test:     ; $(PY) -m tests.run_all
part0:    ; $(PY) -m tests.part0
part1:    ; $(PY) -m tests.part1
part2:    ; $(PY) -m tests.part2
part3:    ; $(PY) -m tests.part3
part4:    ; $(PY) -m tests.part4
peek:     ; $(PY) -m tools.peek $(DATE)
sql:      ; $(PY) -m tools.sql $(FILE)
reset:    ; $(PY) -m tools.reset
submit:   ; $(PY) -m tools.submit
