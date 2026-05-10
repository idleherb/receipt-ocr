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
