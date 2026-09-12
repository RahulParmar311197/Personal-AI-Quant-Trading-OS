.PHONY: install test lint typecheck run docker-up docker-down docker-logs db-upgrade db-current

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

docker-up:
	docker compose -f 27_DEVOPS/docker-compose.dev.yml up --build

docker-down:
	docker compose -f 27_DEVOPS/docker-compose.dev.yml down

docker-logs:
	docker compose -f 27_DEVOPS/docker-compose.dev.yml logs -f

db-current:
	alembic -c 22_DATABASE/alembic.ini current

db-upgrade:
	alembic -c 22_DATABASE/alembic.ini upgrade head
