FROM python:3.11-slim

# System deps: pandoc (documents/reports), fonts, Node.js (mermaid-cli), Chromium (mermaid rendering)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        pandoc \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-fonts-recommended \
        texlive-latex-extra \
        fonts-dejavu \
        nodejs \
        npm \
        chromium \
    && rm -rf /var/lib/apt/lists/*

# Mermaid CLI for diagram rendering (uses Puppeteer + Chromium)
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
RUN npm install -g @mermaid-js/mermaid-cli

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
