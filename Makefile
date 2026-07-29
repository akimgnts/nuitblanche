.PHONY: install test demo run docker-build docker-up docker-down

install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt && playwright install chromium

test:
	cd backend && . .venv/bin/activate && pytest

demo:
	cd backend && . .venv/bin/activate && python -m scripts.generate_demo

run:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down
