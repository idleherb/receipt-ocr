# receipt-ocr

Printed-receipt photo to structured per-line tokens. Sidecar in the
`vorrat-services` TrueNAS app stack; consumed by the
[vorrat](https://github.com/idleherb/vorrat) household-pantry app's
receipt-photo intake flow per
[vorrat ADR-0039](https://github.com/idleherb/vorrat/blob/main/docs/architecture/adrs/0039-receipt-ocr-sidecar.md).

## Status

Walking-skeleton (Phase 1). `/healthz` returns `200 OK`,
`/ocr-receipt` returns `503 model not loaded`. The OCR engine and
parsing rules land in subsequent commits per
[ADR-0039 §6](https://github.com/idleherb/vorrat/blob/main/docs/architecture/adrs/0039-receipt-ocr-sidecar.md).

Implementation roadmap:

- **Phase 1 (this commit):** repo scaffold, `/healthz`, `/ocr-receipt`
  503, CI green on GHCR `:latest`. Deployable into vorrat-services as
  a placeholder that does nothing yet but is reachable.
- **Phase 2 (next):** OCR engine integration (PaddleOCR baseline per
  ADR-0039 §1). `/ocr-receipt` returns real tokens for fixture images.
- **Phase 3:** real-receipt benchmark gate, parsing rules, market
  header detection.

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

Multipart-form image -> structured per-line tokens. Phase 1 always
returns 503; Phase 2 returns the schema documented in
[ADR-0039 §2](https://github.com/idleherb/vorrat/blob/main/docs/architecture/adrs/0039-receipt-ocr-sidecar.md).

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
