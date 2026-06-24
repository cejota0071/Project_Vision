# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# System deps for PDF generation (weasyprint needs extra libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Python deps
COPY experiments/greg_retina/greg_retina/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Copy only this service folder
COPY experiments/greg_retina/greg_retina /app/experiments/greg_retina/greg_retina

# Expose
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -fs http://localhost:8000/health || exit 1

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Entrypoint
CMD ["uvicorn", "experiments.greg_retina.greg_retina.main:app", "--host", "0.0.0.0", "--port", "8000"]

