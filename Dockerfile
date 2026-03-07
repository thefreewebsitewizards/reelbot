FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ src/
COPY static/ static/
COPY assets/ assets/
COPY scripts/ scripts/

# Install the project and all dependencies
RUN pip install --no-cache-dir .

# Create dirs for runtime data
RUN mkdir -p plans tmp

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
