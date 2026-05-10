"""POST /ocr-receipt endpoint.

Phase 2b: the route wires the loaded `OcrRunner` to the parsing
orchestrator. Returns the full `OcrReceiptResponse` per vorrat
ADR-0039 §2a.

Phase-1 / Phase-2a behaviour preserved: when the runner is unloaded
(`is_loaded=False` — e.g. CI smoke with `RECEIPT_OCR_DISABLE_ENGINE=true`,
or a failed engine boot), the endpoint returns 503 with
``{"detail": "model not loaded"}``. The vorrat-app side treats this
as a soft-fail (receipt-photo intake unavailable; barcode scan
unaffected), per vorrat ADR-0035 §3 + ADR-0039 §Negative.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from receipt_ocr.parsing.receipt import parse_receipt
from receipt_ocr.schemas import OcrReceiptResponse

router = APIRouter()

# Conservative cap matches the limit cited in vorrat ADR-0039 §2a.
# Phone-quality JPEGs are ~1-3 MiB; 8 MiB covers the long tail of
# higher-resolution / less-compressed shots without inviting abuse.
_MAX_IMAGE_BYTES = 8 * 1024 * 1024


@router.post("/ocr-receipt", response_model=OcrReceiptResponse)
async def ocr_receipt(
    request: Request,
    image: Annotated[UploadFile, ...],
) -> OcrReceiptResponse:
    """Image -> structured per-line tokens."""
    runner = getattr(request.app.state, "runner", None)
    if runner is None or not runner.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="model not loaded",
        )

    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unsupported content-type: {image.content_type}",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="empty image payload",
        )
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"image exceeds {_MAX_IMAGE_BYTES} bytes",
        )

    started = time.perf_counter()
    raw_lines = runner.ocr(image_bytes)
    ocr_ms = int((time.perf_counter() - started) * 1000)

    return parse_receipt(raw_lines, model_id=runner.model_id, ocr_ms=ocr_ms)
