ARG PYTHON_IMAGE=python:3.13-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.5
FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE} AS base
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./

FROM base AS development
RUN uv sync --frozen
COPY backend backend
COPY alembic.ini ./
CMD ["uv", "run", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS build
RUN uv sync --frozen --no-dev

FROM ${PYTHON_IMAGE} AS production
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --uid 10001 --create-home app
COPY --from=build /app/.venv .venv
COPY backend backend
COPY alembic.ini ./
USER app
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
