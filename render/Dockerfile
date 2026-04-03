FROM python:3.11-slim

# System deps: pandoc, fonts, Chromium (mermaid rendering)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        pandoc \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-fonts-recommended \
        texlive-latex-extra \
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

# Remotion CLI + React deps for video rendering (global)
RUN npm install -g @remotion/cli@4.0.0 remotion@4.0.0 react@18 react-dom@18 zod@3 && \
    echo "=== npm global prefix ===" && npm config get prefix && \
    echo "=== which remotion ===" && which remotion || echo "not in PATH" && \
    echo "=== find remotion ===" && find / -name "remotion" -type f 2>/dev/null | head -5 || true

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# ADR-157: Install Remotion composition deps (React + @remotion/cli)
RUN cd /app/skills/video/composition && \
    npm install 2>&1 && \
    echo "=== Remotion binary check ===" && \
    ls -la node_modules/.bin/remotion && \
    echo "=== Remotion version ===" && \
    node_modules/.bin/remotion --version

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
