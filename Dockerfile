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
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Default command — overridden per service in docker-compose.yml
CMD ["python", "server.py"]
