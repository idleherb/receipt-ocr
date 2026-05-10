# syntax=docker/dockerfile:1.7
# Multi-stage build for receipt-ocr.
#
# Walking-skeleton (Phase 1): no OCR engine yet, image is small (~150 MB).
# Phase 2 will add PaddleOCR (or chosen backend per ADR-0039 §1) — the
# OCR model files are mounted at runtime via Docker volume, never baked
# into the image.

FROM python:3.12-slim AS builder

# uv handles the venv + dep install. No native build deps needed in
# Phase 1 (FastAPI + uvicorn are pure-Python wheels). Phase 2 may add
# build-essential / libgl1 / libglib2.0 depending on OCR backend.
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# No native runtime deps in Phase 1. Phase 2 may add libgomp1 / libgl1
# depending on OCR backend.

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src ./src
COPY pyproject.toml ./

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

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
