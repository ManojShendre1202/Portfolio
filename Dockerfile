# Base image — slim keeps it small
FROM python:3.11-slim

# System dependencies
# libportaudio2   — not needed (Vian AI audio is Android-side only)
# build-essential — needed to compile some pip packages
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy requirements first — layer cache means pip only reruns if requirements change
COPY requirements.txt .
# CPU-only torch wheel — installed first so the plain requirements.txt install
# below finds a matching version already satisfied and skips pulling the
# default PyPI (CUDA-bundled) build, which drags in several GB of unused
# nvidia-* packages on a GPU-less VM.
RUN pip install --no-cache-dir torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
# spaCy language model — not a normal pip package (see requirements.txt's
# comment), doc_retrieval.py loads it eagerly at import time for keyword-
# seed POS tagging, so both the django and dockyard services need it or
# they crash on startup.
RUN python -m spacy download en_core_web_sm

# Copy the rest of the code
COPY . .

# Bakes admin's CSS/JS into staticfiles/ for WhiteNoise to serve — safe to
# run in both django and dockyard images even though only django serves it.
RUN python manage.py collectstatic --noinput

# Default command — overridden per service in docker-compose.yml
CMD ["python", "server.py"]
