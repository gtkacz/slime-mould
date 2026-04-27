FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY benchmark ./benchmark
COPY configs ./configs
COPY src ./src

RUN uv sync --frozen --extra viz --no-dev

EXPOSE 8000

CMD ["uv", "run", "zipmould", "viz", "serve", "--host", "0.0.0.0", "--port", "8000"]
