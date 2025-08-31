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

# Expose the port the app runs on
EXPOSE 8000

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser || true
USER appuser

# Healthcheck route should be available in the app
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD curl -f http://127.0.0.1:8000/_health || exit 1

# Default command for production (Gunicorn)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app.main:create_app()"]