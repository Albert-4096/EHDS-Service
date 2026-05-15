FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Tesseract, Poppler (for pdf2image)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ron \
    poppler-utils \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
