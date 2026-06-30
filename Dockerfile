FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies (WeasyPrint + build tools)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libgdk-pixbuf-2.0-0 \
    libxml2-dev \
    libxslt1-dev \
    shared-mime-info \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code from the repo root context
COPY backend/ ./

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Run migrations and start the server
CMD ["./start.sh"]
