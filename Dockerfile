FROM python:3.11-slim

# Set the working directory
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if needed (uncomment for OCR)
# RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libgl1 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend (assuming backend/ folder containing app/)
COPY backend/ ./backend

# Ensure the backend package is in the PYTHONPATH
ENV PYTHONPATH=/app/backend

WORKDIR /app/backend

# Expose the port the app runs on
EXPOSE 8000

# Default command for production (Gunicorn)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app.main:create_app()"]