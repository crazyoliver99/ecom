FROM python:3.12-slim

WORKDIR /srv

# Install pinned dependencies first so Docker caches this layer.
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Then copy the application code.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
