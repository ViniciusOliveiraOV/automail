FROM python:3.11-slim

# Use a conventional application directory inside the image. This layout is
# host-agnostic and works the same whether the build runs on Linux, macOS or
# Windows hosts because Docker packages the build context into a tar stream.
WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if needed (uncomment for OCR)
# RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libgl1 && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to maximize layer caching
COPY requirements.txt /usr/src/app/requirements.txt
RUN pip install --upgrade pip && \
	pip install --no-cache-dir -r /usr/src/app/requirements.txt

# Copy the full project into the image. This keeps paths consistent across
# hosts (no Windows/Unix path differences matter inside the container).
COPY . /usr/src/app

# Ensure the repository root is on PYTHONPATH so `import app` resolves.
ENV PYTHONPATH=/usr/src/app

# Expose the (conventional) HTTP port used by many PaaS; the runtime will
# still provide a PORT env var which we use at runtime so the container can
# adapt to whatever port the host assigns.
EXPOSE 8080

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser || true
USER appuser

# Healthcheck route should be available in the app. Install curl so the
# healthcheck binary exists; this keeps the healthcheck reliable inside the
# slim base image.
USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD curl -f http://127.0.0.1:$PORT/_health || exit 1
# Copy startup wrapper and make it executable
COPY --chown=appuser:appuser start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Default command uses the startup wrapper which validates $PORT then execs
# gunicorn. Using exec means PID 1 is the gunicorn process (cleaner signals).
CMD ["/usr/local/bin/start.sh"]