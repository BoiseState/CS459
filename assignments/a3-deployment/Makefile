# Run these inside the app container: docker compose run --rm app
.PHONY: doctor bootstrap train test test1 test2 test3 test4 test5 drill promote submit backup restore

doctor:
	@python src/doctor.py

bootstrap:
	python src/bootstrap.py

train:
	python src/train.py

test:
	python -m pytest -q -p no:cacheprovider tests

test1:
	python -m pytest -q -p no:cacheprovider tests/test_part1.py
test2:
	python -m pytest -q -p no:cacheprovider tests/test_part2.py
test3:
	python -m pytest -q -p no:cacheprovider tests/test_part3.py
test4:
	python -m pytest -q -p no:cacheprovider tests/test_part4.py
test5:
	python -m pytest -q -p no:cacheprovider tests/test_part5.py

drill:
	python src/drill.py

promote:
	python src/promote.py

submit:
	python src/export_state.py
	rm -f submission.zip
	zip -qr submission.zip src answers config submission mlflow_data -x '*.pyc' '*__pycache__*'
	@echo "Wrote submission.zip. Upload it to Canvas with your PDF."

# A copy of your MLflow data (runs, models, registry) in backups/, on your own disk.
backup:
	@mkdir -p backups
	@cd mlflow_data && zip -qr ../backups/mlflow-$$(date +%Y%m%d-%H%M%S).zip . -x '.gitkeep'
	@ls -1t backups | head -1 | sed 's|^|Backed up to backups/|'

# Put a backup back. Stop the server first; see README, "If you lose your MLflow data".
restore:
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/<name>.zip" && exit 1)
	@test -f "$(FILE)" || (echo "No such file: $(FILE)" && exit 1)
	@find mlflow_data -mindepth 1 ! -name .gitkeep -exec rm -rf {} +
	@python -m zipfile -e "$(FILE)" mlflow_data/
	@echo "Restored $(FILE). Now start the server: docker compose up -d mlflow"
