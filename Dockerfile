FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for matplotlib
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY gbm/ ./gbm/
COPY tests/ ./tests/

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "gbm.cli", "--help"]

