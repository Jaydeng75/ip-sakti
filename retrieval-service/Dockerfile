FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/huggingface

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.3,<3.0" \
    && pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN mkdir -p /models/huggingface && chown -R app:app /app /models
USER app
EXPOSE 8200
HEALTHCHECK --interval=30s --timeout=4s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8200/health/live', timeout=3)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8200"]
