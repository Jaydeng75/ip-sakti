FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/huggingface

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt .
RUN apt-get update \
    && apt-get install --no-install-recommends --yes build-essential \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.3,<3.0" \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge --auto-remove --yes build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY app.py .
RUN mkdir -p /models/huggingface && chown -R app:app /app /models
USER app
EXPOSE 8100
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
