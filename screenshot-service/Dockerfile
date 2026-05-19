FROM python:3.11-slim

WORKDIR /app

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium and its OS dependencies
RUN playwright install chromium --with-deps

# Copy application source
COPY app.py .

# Ensure screenshots directory exists
RUN mkdir -p /app/screenshots

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
