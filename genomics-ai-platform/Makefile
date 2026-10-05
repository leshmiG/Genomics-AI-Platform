.PHONY: setup test lint train ingest run up demo
AI=services/ai-service
setup: ; cd $(AI) && pip install -e ".[dev]"
lint: ; cd $(AI) && ruff check app tests
test: ; cd $(AI) && python -m pytest -q
train: ; cd $(AI) && python -m app.ml.train --out artifacts/models
ingest: ; cd $(AI) && python -m app.rag.ingest
run: train ingest ; cd $(AI) && uvicorn app.main:app --reload
up: ; docker compose up --build
demo: ; bash scripts/demo.sh
