FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for matplotlib and scipy
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY gbm/ ./gbm/
COPY tests/ ./tests/
COPY pyproject.toml .
COPY setup.py .

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "gbm.cli", "--help"]

