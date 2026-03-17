# Root Dockerfile for yarnnn-render service (ADR-118)
# Render.com MCP creates Docker services with context=. and path=./Dockerfile
# This delegates to the render/ subdirectory.

FROM python:3.11-slim

# Install pandoc for document rendering (markdown → PDF/DOCX)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        pandoc \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-fonts-recommended \
        texlive-latex-extra \
        fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY render/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY render/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
