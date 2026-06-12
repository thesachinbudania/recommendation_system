# --- BUILD Stage ---
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=3.13 \
    UV_PROJECT_ENVIRONMENT=/app \
    DJANGO_SETTINGS_MODULE=recommendation_system.production

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    curl libpq-dev

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN uv venv /app

WORKDIR /app

COPY pyproject.toml /app
COPY uv.lock /app
COPY README.md /app
COPY recommendation_system/manage.py /app

RUN uv sync

COPY recommendation_system/ /app/

RUN /app/bin/python manage.py collectstatic --noinput

# --- Production Stage ---
FROM python:3.13-slim AS production

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev

COPY --from=builder /app /app

WORKDIR /app

RUN groupadd -r django && useradd -r -g django -d /app -s /bin/bash django && \
    chown -R django:django /app

USER django

CMD ["/app/bin/gunicorn", "--bind", "0.0.0.0:8000", "recommendation_system.wsgi:application"]

EXPOSE 8000