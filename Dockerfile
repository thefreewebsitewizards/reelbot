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
COPY shared-context/ shared-context/

# Install the project and all dependencies
RUN pip install --no-cache-dir .

# Pre-download Whisper model into the image so it doesn't re-download every deploy
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

# Create dirs for runtime data
RUN mkdir -p plans tmp

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
