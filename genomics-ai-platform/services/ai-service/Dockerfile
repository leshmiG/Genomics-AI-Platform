FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -m app
WORKDIR /srv
COPY services/ai-service/pyproject.toml ./
COPY services/ai-service/app ./app
COPY services/ai-service/data ./data
RUN pip install --no-cache-dir -e ".[aws,pg]"
# Build the model + RAG index at image build time so the container is ready immediately.
# (In real MLOps the model comes from a registry; see docs/ARCHITECTURE.md.)
ENV GAI_MODEL_DIR=/srv/artifacts/models GAI_INDEX_DIR=/srv/artifacts/index GAI_KNOWLEDGE_DIR=/srv/data/knowledge
RUN python -m app.ml.train --out /srv/artifacts/models && python -m app.rag.ingest && chown -R app /srv
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
