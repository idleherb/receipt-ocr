# receipt-ocr

Printed-receipt photo to structured per-line tokens. Sidecar in the
`vorrat-services` TrueNAS app stack; consumed by the
[vorrat](https://github.com/idleherb/vorrat) household-pantry app's
receipt-photo intake flow per
[vorrat ADR-0039](https://github.com/idleherb/vorrat/blob/main/docs/architecture/adrs/0039-receipt-ocr-sidecar.md).

## Status

Phase 2b (current). PaddleOCR engine + parser pipeline wired
end-to-end. `/healthz` reflects the runner's load state; `/ocr-receipt`
returns the full `OcrReceiptResponse` (market header, parsed item
lines, totals) for loaded runners, and 503 cleanly for unloaded /
stub mode (CI smoke). Real-receipt benchmark gate per ADR-0039 §1
runs in Phase 3.

Implementation roadmap (per
[ADR-0039 §6](https://github.com/idleherb/vorrat/blob/main/docs/architecture/adrs/0039-receipt-ocr-sidecar.md)):

- **Phase 1 (shipped):** repo scaffold, `/healthz`, `/ocr-receipt` 503,
  CI green on GHCR `:latest`.
- **Phase 2a (current commit):** PaddleOCR engine wired in via the
  `OcrRunner` Protocol (`inference/runner.py`); concrete backend in
  `inference/paddle_runner.py`. Lifespan loads the engine at startup;
  `/healthz` reports `model_loaded:true` on the live server once warm.
  CI runs with `RECEIPT_OCR_DISABLE_ENGINE=true` to skip the ~100 MB
  model download.
- **Phase 2b (next):** parser + `/ocr-receipt` wire-up. Engine output
  -> structured per-line tokens (price, multiplier, tax-marker) +
  market-header detection.
- **Phase 3:** real-receipt benchmark gate per ADR-0039 §1.

## API

### `GET /healthz`

```json
{
  "ok": true,
  "channel": "main",
  "commit": "abcdef0",
  "version": "2026.5.10",
  "model_loaded": false,
  "model_id": "unloaded"
}
```

`model_loaded` flips to `true` once Phase 2 wires up the OCR engine.

### `POST /ocr-receipt`

Multipart-form image (`image/jpeg` or `image/png`, ≤ 8 MiB) ->
structured per-line tokens per
[ADR-0039 §2a](https://github.com/idleherb/vorrat/blob/main/docs/architecture/adrs/0039-receipt-ocr-sidecar.md).
Returns 503 with `{"detail": "model not loaded"}` when the runner
isn't loaded (CI smoke / engine boot failure) — this is the
soft-fail signal that lets vorrat-app degrade the receipt-photo
intake gracefully without breaking other paths.

## Running locally

```sh
uv sync --extra dev
uv run uvicorn receipt_ocr.main:app --host 0.0.0.0 --port 8003
# In another shell:
curl http://localhost:8003/healthz
```

## Tests

```sh
uv run --frozen pytest
```

Phase 1 covers: `/healthz` shape + status, `/ocr-receipt` 503 stub,
`Settings` env-prefix + defaults. 90 % branch-coverage gate enforced.

## Deployment

Deployed as a service block in the
[idleherb/vorrat-services](https://github.com/idleherb/vorrat-services)
compose stack on TrueNAS. Single-track `:latest` image on GHCR; pushed
on every merge to `main`; Watchtower picks up changes within ~5 min.
See [vorrat ADR-0035](https://github.com/idleherb/vorrat/blob/main/docs/architecture/adrs/0035-service-topology-consolidation.md)
for the topology and
[vorrat-services/docs/sidecar-onboarding.md](https://github.com/idleherb/vorrat-services/blob/main/docs/sidecar-onboarding.md)
for the deployment workflow.

## License

Deferred along with vorrat's main-repo license (vorrat ADR-0014).

## Maintainer

[idleherb](https://github.com/idleherb)
