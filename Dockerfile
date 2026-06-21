# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md ./
COPY src ./src
COPY graphql ./graphql
COPY templates ./templates
COPY .env.example ./

RUN python -m pip install --upgrade pip && \
    python -m pip install --editable .

USER app

ENTRYPOINT ["github-project-digest"]
