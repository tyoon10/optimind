# Use official lightweight Python image
FROM python:3.11-slim

# Install system dependencies (Git is required for Journal Sync)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Trust all git directories (fixes "dubious ownership" error in Cloud Run)
RUN git config --global --add safe.directory '*'

# Copy the rest of the application
COPY . .

# Expose the port (Cloud Run sets $PORT environment variable, default 8080)
ENV PORT=8080

# Command to run the application
# We use $PORT var correctly for Cloud Run
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"
