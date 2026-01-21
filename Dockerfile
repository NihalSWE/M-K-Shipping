# Use python 3.10
FROM python:3.10-slim

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
    libcairo2-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/