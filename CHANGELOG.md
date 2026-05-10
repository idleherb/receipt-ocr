# Changelog

All notable changes to this sidecar are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
in shape but uses `[Unreleased]` only — sidecars don't carry releases
(per vorrat ADR-0035 §2; push-to-main → CI → GHCR `:latest` →
Watchtower swap).

## [Unreleased]

### Added
- Initial walking-skeleton per vorrat ADR-0039 §6 Phase 1.
- FastAPI app with `/healthz` (returns `model_loaded: false`).
- `POST /ocr-receipt` route stubbed at HTTP 503 (model not loaded);
  consumer-side integration in vorrat-app can develop against the
  stable URL while Phase 2 lands the OCR engine.
- Dockerfile (uv builder + python:3.12-slim runtime), CI gates
  (ruff format/lint, ty type-check, pytest with 90 % branch-coverage
  floor), build workflow (smoke-test + GHCR `:latest` push on main).
- Tests covering `/healthz` shape, `/ocr-receipt` 503 stub, and
  `Settings` env-prefix + defaults.
- **Phase 2a (this commit): PaddleOCR engine wired into the runtime.**
  `inference/runner.py` defines an `OcrRunner` Protocol; the real
  backend lives in `inference/paddle_runner.py` (coverage-omitted,
  per ADR-0039 §6 + the off-classifier convention) and is loaded at
  lifespan-startup. `/healthz` now reflects `runner.is_loaded`
  truthfully — the live server reports `model_loaded:true` once the
  engine warms up; CI uses `RECEIPT_OCR_DISABLE_ENGINE=true` to skip
  the ~100 MB model download and stays in stub mode. `/ocr-receipt`
  remains 503 until Phase 2b lands the parsing layer; on the live
  server it 503s cleanly when the stub is active.
- New deps: `paddleocr>=2.7`, `paddlepaddle>=2.6`, `numpy<2.0`,
  `Pillow>=10.0`. Image grows from ~150 MB to ~1.2 GB (paddlepaddle
  amd64 wheel is ~700 MB; documented in vorrat ADR-0039 §Negative).
- Dockerfile gains `libgomp1`, `libgl1`, `libglib2.0-0` runtime deps
  (OpenMP for paddle's CPU threading; OpenCV for paddleocr's image
  pre-processing).
- `requires-python` capped at `<3.14` because paddlepaddle wheels
  currently ship for cp312/cp313 only. Revisit when cp314 lands.
