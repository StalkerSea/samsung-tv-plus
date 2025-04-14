# Build stage for compiling dependencies
FROM python:3.13-alpine AS builder

# Install build dependencies
RUN apk add --no-cache build-base

# Install dependencies directly
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final stage with minimal footprint
FROM python:3.13-alpine
WORKDIR /app

# Copy only the installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application files
COPY . .

# Expose port
EXPOSE 80/tcp

# Environment variables for optimization
ENV IS_DOCKER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONTRACEMALLOC=0
ENV PYTHONOPTIMIZE=2
ENV PYTHONHASHSEED=random
ENV PYTHONDONTWRITEBYTECODE=1

# Run with optimized flags
CMD [ "python", "-u", "./app.py" ]
