# Changelog

All notable changes to this sidecar are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
in shape but uses `[Unreleased]` only — sidecars don't carry releases
(per vorrat ADR-0035 §2; push-to-main → CI → GHCR `:latest` →
Watchtower swap).

## [Unreleased]

### Fixed — Phase 2c: paddlepaddle 3.3 PIR-executor crash on real images
- Pinning `paddlepaddle<3.3` works around a PIR-executor + oneDNN-
  instruction bug that raised `NotImplementedError(Convert
  PirAttribute2RuntimeAttribute not support pir::ArrayAttribute<
  pir::DoubleAttribute>)` at every predict-time call against
  PP-OCRv5 / PP-OCRv4 detection models. paddle 3.2.x runs cleanly.
- Discovered post-Phase-2b deploy: live `/ocr-receipt` 500'd on real
  receipt-photo input until this pin landed. Runtime flags
  (`FLAGS_use_mkldnn=0`, `FLAGS_enable_pir_in_executor=false`) and
  detection-model pinning (PP-OCRv4_mobile_det) did not sidestep the
  issue. Revisit the pin once paddlepaddle ships 3.3.x patch or 3.4.

### Added — Phase 2b: parser + `/ocr-receipt` wire-up
- New `parsing/` module:
  - `line_parser.parse_item_line` extracts
    `(raw_token, price_eur, multiplier, line_total_eur, tax_marker)`
    from receipt-line text, handling both single-line items and
    `1,99 € x 2` multiplier expressions, plus optional `*A` / ` AW`
    tax-marker suffixes.
  - `market_header.identify_market` matches header lines against a
    small per-chain regex dictionary (Kaufland, Edeka, Rewe, ALDI Süd
    + Nord, Lidl, Penny, Netto, dm, Rossmann) and extracts a coarse
    `store_label_guess` (slugified city) from the
    `<PLZ> <City>-<District>` line common to German receipt headers.
  - `receipt.parse_receipt` orchestrates: top-down split into
    header / item-block / totals; runs the line-parser on item-block
    lines; pulls `Posten:` count + `SUMME` value from totals.
- `POST /ocr-receipt` now wired end-to-end (engine → parser → full
  `OcrReceiptResponse` per vorrat ADR-0039 §2a) for loaded runners.
  Stub-runner / unloaded path continues to 503.
- New schemas: `MarketGuess`, `ReceiptLine`, `ReceiptTotals`,
  `OcrReceiptResponse`. Multipart-image input cap at 8 MiB (`413`
  over the cap), 422 on non-image content-types.
- Tests: 53 total, 98 % branch-coverage. Real Kaufland-receipt-line
  fixtures + the orchestrator + the `/ocr-receipt` integration path
  via httpx.

### Added — Phase 2a: PaddleOCR engine wired into the runtime
- `inference/runner.py` defines an `OcrRunner` Protocol; the real
  backend lives in `inference/paddle_runner.py` (coverage-omitted,
  per ADR-0039 §6 + the off-classifier convention) and is loaded at
  lifespan-startup. `/healthz` reflects `runner.is_loaded` truthfully
  — the live server reports `model_loaded:true` once the engine
  warms up; CI uses `RECEIPT_OCR_DISABLE_ENGINE=true` to skip the
  ~100 MB model download and stays in stub mode.
- New deps: `paddleocr>=2.7`, `paddlepaddle>=2.6`, `numpy<2.0`,
  `Pillow>=10.0`. Image size: ~480 MB (well below the ~1.2 GB
  worst-case projected in ADR-0039 §Negative).
- Dockerfile gains `libgomp1`, `libgl1`, `libglib2.0-0` runtime deps
  (OpenMP for paddle's CPU threading; OpenCV for paddleocr's image
  pre-processing). `PADDLE_PDX_CACHE_HOME=/models/paddlex` set
  pre-import so model downloads land in the named volume.
- `requires-python` capped at `<3.14` because paddlepaddle wheels
  currently ship for cp312/cp313 only. Revisit when cp314 lands.

### Added — Phase 1: walking-skeleton
- Initial scaffold per vorrat ADR-0039 §6 Phase 1.
- FastAPI app with `/healthz` returning `model_loaded: false`.
- `POST /ocr-receipt` stubbed at HTTP 503 ("model not loaded");
  consumer-side integration in vorrat-app developed against the
  stable URL while Phase 2 lands the OCR engine.
- Dockerfile (uv builder + python:3.12-slim runtime), CI gates
  (ruff format/lint, ty type-check, pytest with 90 % branch-coverage
  floor), build workflow (smoke-test + GHCR `:latest` push on main).
- Tests covering `/healthz` shape, `/ocr-receipt` 503 stub,
  `Settings` env-prefix + defaults.
