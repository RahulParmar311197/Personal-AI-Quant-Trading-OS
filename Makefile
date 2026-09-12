.PHONY: install test lint typecheck run

install:
	python -m pip install -e '.[dev]'

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy 20_API/app

run:
	uvicorn app.main:app --app-dir 20_API --host 127.0.0.1 --port 8000
