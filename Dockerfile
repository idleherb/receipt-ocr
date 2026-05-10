# syntax=docker/dockerfile:1.7
# Multi-stage build for receipt-ocr.
#
# Phase 2a: PaddleOCR engine integration. paddlepaddle's amd64 wheel is
# ~700 MB, paddleocr is small. Image grows to ~1.2 GB. The OCR model
# files (~100 MB total: detection + recognition + textline-orientation)
# are pulled by PaddleOCR on first init into the named Docker volume
# mounted at /models — never baked into the image.

FROM python:3.12-slim AS builder

# uv handles the venv + dep install. paddlepaddle ships sdists for some
# transitive deps that need a compiler; we keep build-essential in the
# builder stage only and discard the runtime stage.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

ARG UV_VERSION=0.11.4
RUN pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /app
# README.md is referenced as `readme` in pyproject.toml — hatchling
# reads it during `uv pip install -e`. Without the COPY, the install
# bails with `OSError: Readme file does not exist: README.md`.
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python -e ".[dev]"

COPY src ./src

FROM python:3.12-slim AS runtime

# Native runtime deps for paddlepaddle + paddleocr:
#   - libgomp1: OpenMP runtime for paddle's CPU threading
#   - libgl1, libglib2.0-0: OpenCV (paddleocr's image-pre-processing
#     dep) loads libGL.so.1 + libgthread-2.0.so.0 even on headless
#     servers. Without these, `import cv2` fails at import time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src ./src
COPY pyproject.toml ./

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# PaddleX (PaddleOCR's underlying model-management layer) reads this
# env-var at module load to decide where to download / cache official
# models. Pointing it at the mounted /models volume makes downloads
# survive container restarts. Must be set before any paddleocr/paddlex
# import — Python-side `os.environ.setdefault()` is too late because
# paddlex computes its CACHE_DIR at import time.
ENV PADDLE_PDX_CACHE_HOME=/models/paddlex

# Pre-create /models with UID 1000 ownership inside the image. Compose
# stacks set `user: '1000:1000'`; without this the container's worker
# would hit `Permission denied` on the named volume because Docker
# would mount /models with root-owned defaults. When the operator's
# named volume is empty on first mount, Docker seeds it from the
# image — so these permissions carry over and the OCR engine can write
# its model cache. Existing volumes with broken perms must be wiped
# once before this fix takes effect.
#
# /models is empty in Phase 1 because no OCR engine downloads anything
# yet, but the directory + perms set up the contract for Phase 2.
RUN mkdir -p /models /app/data && \
    chown -R 1000:1000 /models /app

ARG VORRAT_BUILD_CHANNEL=dev
ARG VORRAT_BUILD_SHA=unknown
ARG VORRAT_BUILD_DATE=unknown
ENV RECEIPT_OCR_BUILD_CHANNEL=${VORRAT_BUILD_CHANNEL}
ENV RECEIPT_OCR_BUILD_SHA=${VORRAT_BUILD_SHA}
ENV RECEIPT_OCR_BUILD_DATE=${VORRAT_BUILD_DATE}

EXPOSE 8003

# uvicorn binds to 0.0.0.0 inside the container. --log-level warning
# silences the per-request access log per vorrat CLAUDE.md hard rule
# 10 (production log level is WARNING+errors only).
CMD ["uvicorn", "receipt_ocr.main:app", "--host", "0.0.0.0", "--port", "8003", "--log-level", "warning"]
