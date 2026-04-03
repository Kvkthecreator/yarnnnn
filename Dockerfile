# Root Dockerfile for yarnnn-output-gateway service (ADR-118)
# Render.com builds Docker services with context=. and path=./Dockerfile

FROM python:3.11-slim

# System deps: pandoc (documents), fonts, Chromium (mermaid rendering), curl (NodeSource)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        pandoc \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-fonts-recommended \
        texlive-latex-extra \
        lmodern \
        fonts-dejavu \
        chromium \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 LTS via NodeSource (proper install with node, npm, npx in PATH)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    node --version && npm --version && npx --version

# Mermaid CLI for diagram rendering (uses Puppeteer + Chromium)
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
RUN npm install -g @mermaid-js/mermaid-cli

# Remotion CLI for video rendering (global — available to subprocess)
RUN npm install -g @remotion/cli@4.0.0

WORKDIR /app
COPY render/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY render/ .

# Install Remotion composition deps (React + Remotion)
RUN cd /app/skills/video/composition && npm install

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
