FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_NO_INTERACTION=1

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        clamav \
        clamav-daemon \
        clamav-freshclam \
        libgl1-mesa-dri \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        libgcc-s1 \
        fonts-dejavu-core \
        fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Initialize ClamAV database (run as root before switching to appuser)
RUN freshclam --quiet || echo "ClamAV database update attempted"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies via Poetry (no virtualenv)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code into /app
COPY app/ ./app/
COPY mcp_server/ ./mcp_server/
COPY mcp_client/ ./mcp_client/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY openapi.yaml ./
COPY redocly.yaml ./
COPY docs/ ./docs/
COPY tests/ ./tests/

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application directly with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]