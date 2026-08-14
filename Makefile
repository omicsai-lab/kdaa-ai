.PHONY: install install-app test lint format demo demo-all benchmark stress-test figures schemas api app docker release-check package clean

install:
	python -m pip install -e .

install-app:
	python -m pip install -e ".[app,dev]"

test:
	pytest --cov=kdaa --cov-report=term-missing

lint:
	ruff check .
	ruff format --check src tests app scripts

format:
	ruff format src tests app scripts
	ruff check --fix .

demo:
	kdaa demo --scenario researcher --output results/demo

demo-all:
	bash scripts/run_demo.sh

benchmark:
	bash scripts/run_benchmark.sh

stress-test:
	bash scripts/run_robustness.sh

figures:
	python scripts/build_figures.py

schemas:
	python scripts/generate_demo_data.py

api:
	uvicorn kdaa.api:app --reload --host 0.0.0.0 --port 8000

app:
	streamlit run app/streamlit_app.py

docker:
	docker compose up --build

release-check:
	python scripts/check_release.py

package: release-check
	rm -rf dist
	mkdir -p dist
	python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
	python scripts/package_release.py --output dist

clean:
	rm -rf .coverage .pytest_cache .ruff_cache htmlcov build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
