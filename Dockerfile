FROM python:3.12-slim-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.30 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# uv.lock is committed (make setup writes it); the glob keeps a first build
# working before it exists, at the cost of an unpinned resolution.
COPY pyproject.toml uv.lock* ./
# The lock still holds the CUDA build of torch and its nvidia-* and triton packages (about 5 GB).
# Install everything else as locked, then torch from the CPU index at the locked version
# (ADR-0004: embeddings run on CPU). Once `uv add torch` has switched the lock to the CPU
# build, this block can go back to a plain `uv sync --locked --no-dev --no-install-project`.
RUN if [ -f uv.lock ]; then \
      uv venv && \
      uv export --frozen --no-dev --no-hashes --no-emit-project -o /tmp/all.txt && \
      TORCH_VERSION="$(sed -n 's/^torch==\([0-9.]*\).*/\1/p' /tmp/all.txt | head -n1)" && \
      grep -vE '^(torch|triton|nvidia-)' /tmp/all.txt > /tmp/rest.txt && \
      uv pip install --no-deps -r /tmp/rest.txt && \
      uv pip install --no-deps --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}" ; \
    else echo "lockfile: no uv.lock committed, resolving unpinned (run uv lock and commit uv.lock)"; uv sync --no-dev --no-install-project; fi
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
# Read at runtime: the versioned prompts, the golden contracts behind "Load the 6 golden
# contracts", and the committed model replies that let extraction and Q&A run without a key.
COPY prompts ./prompts
COPY data ./data
COPY llm_cache ./llm_cache
# The embedding model is downloaded once here, so a running container never needs the network
# for it (Q-016). It lands in /app/models, where Settings.embedding_model_dir looks.
RUN /app/.venv/bin/python -m app.retrieval.fetch

FROM python:3.12-slim-bookworm
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
# One worker by default: each worker loads its own copy of the embedding model, and the free
# hosting tiers have little memory. Raise WEB_CONCURRENCY on a bigger machine.
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8080 WEB_CONCURRENCY=1
USER app
EXPOSE 8080
# gunicorn supervises uvicorn workers (uvicorn-worker is the maintained home
# of UvicornWorker; uvicorn.workers is deprecated). WEB_CONCURRENCY sets the
# worker count. The shell form reads PORT, so a host that assigns the port (Cloud Run, Render,
# Hugging Face with app_port) works without a rebuild. `make dev` runs uvicorn directly with --reload.
CMD ["sh", "-c", "exec gunicorn 'app.main:create_app()' -k uvicorn_worker.UvicornWorker --bind 0.0.0.0:${PORT} --access-logfile - --graceful-timeout 30 --timeout 60"]
