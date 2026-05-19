# Use a lightweight python image instead of full Microsoft image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY BE/requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the fuzzer package and install it
COPY lookalike_fuzzer/ ./lookalike_fuzzer/
RUN pip install -e ./lookalike_fuzzer

# Copy the entire backend directory
COPY BE/ .

# Ensure necessary directories exist
RUN mkdir -p screenshots GeoIP

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
