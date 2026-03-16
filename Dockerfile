# Use python 3.12
FROM python:3.12-slim

# Prevent python from writing pyc files to disc and buffering stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
# UPDATED: Added pkg-config, libcairo2-dev, and python3-dev
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    pkg-config \
    python3-dev \
    \
    # WeasyPrint runtime deps
    libcairo2 \
    libcairo2-dev \
    \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    \
    libgdk-pixbuf-2.0-0 \
    \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/