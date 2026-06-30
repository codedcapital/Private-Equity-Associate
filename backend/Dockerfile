FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (including WeasyPrint dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libgdk-pixbuf2.0-0 \
    libxml2-dev \
    libxslt1-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY backend/ ./

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Run migrations and start the server
CMD ["./start.sh"]
