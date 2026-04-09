# Contexto = pasta `temporal/` (ex.: Railway com Root Directory = `temporal`).
# Build local: na raiz do monorepo → docker build -f temporal/Dockerfile temporal
FROM python:3.12-slim-bookworm

WORKDIR /worker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run_worker.py"]
