"""POST /ocr-receipt endpoint.

Phase 1 (this commit): the route exists but always 503s with
``{"detail": "model not loaded"}`` because no OCR engine is wired up
yet. The route is here so that:

  - The CI smoke-test can assert on the 503 response body, mirroring
    the off-classifier's pattern (`/classify` returning 503 cleanly
    when no model is mounted).
  - The vorrat-app can develop against a stable URL surface; consumers
    only need to flip a feature flag once Phase 2 lands.

Phase 2 (next commit) replaces the body with the real OCR + parsing
pipeline. The wire-shape (multipart image in, structured token list
out) is documented in vorrat ADR-0039 §2.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, status

router = APIRouter()


@router.post("/ocr-receipt", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
async def ocr_receipt(image: UploadFile) -> None:
    """Image -> structured per-line tokens. Phase 1 stub."""
    # Future Phase-2 code path: read image bytes, hand to OCR engine,
    # parse line tokens, return structured response per ADR-0039 §2.
    # For now: declare the lack of a model loudly so consumers don't
    # silently get fake data.
    _ = image  # accepted by the form parser, contents discarded in stub
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="model not loaded",
    )
