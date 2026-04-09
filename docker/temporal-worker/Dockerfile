# Build com contexto na raiz do monorepo:
#   docker build -f docker/temporal-worker/Dockerfile -t liquida-temporal-worker .
# Com Root Directory = `temporal` no Railway, use `temporal/Dockerfile` (path `Dockerfile`).
FROM python:3.12-slim-bookworm

WORKDIR /worker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY temporal/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY temporal/ .

CMD ["python", "run_worker.py"]
