"""PaddleOCR-backed OCR runner.

This module is **excluded from coverage** (see `pyproject.toml` →
`[tool.coverage.run] omit`) because exercising it requires PaddleOCR's
model files on disk (~100 MB pulled from PaddlePaddle's CDN on first
init), which is too heavy for the unit-test path. Behaviour is
verified via the integration smoke flow (Docker container with the
real engine, hit `/ocr-receipt` against a fixture image), and on the
live server post-Watchtower-deploy.

The Protocol seam (`receipt_ocr.inference.runner.OcrRunner`) lets unit
tests stub this entirely.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from receipt_ocr.inference.runner import OcrRunner, RawOcrLine

log = logging.getLogger(__name__)


class PaddleRunner:
    """Concrete `OcrRunner` wrapping PaddleOCR.

    First instantiation downloads the recognition + detection models
    from PaddlePaddle's CDN into `model_dir` (mounted from the named
    Docker volume in production). Subsequent containers hit the cache
    and warm-start in seconds.

    The constructor blocks until the engine is ready; if PaddleOCR
    fails to initialise (missing model, network outage on first
    download, library import error), the caller catches the exception
    and falls through to ``_UnloadedStub``.
    """

    def __init__(self, lang: str = "german") -> None:
        # Lazy import — keeps the test-suite import-free of the paddle
        # ecosystem (otherwise unit tests would pay paddle's cold-start
        # cost on every collection pass).
        from paddleocr import PaddleOCR  # noqa: PLC0415

        # Model cache location is controlled by PADDLE_PDX_CACHE_HOME,
        # set in the Dockerfile to /models/paddlex (the named Docker
        # volume). Setting it from Python here would be too late —
        # paddlex resolves the env var at module-load time, and
        # `from paddleocr import ...` triggers that.
        #
        # PaddleOCR 3.x auto-downloads its detection / recognition /
        # textline-orientation models on first init based on `lang`.
        # Subsequent inits hit the cache and warm-start in seconds.
        #
        # paddlepaddle is pinned `<3.3` in pyproject.toml because
        # 3.3 has a PIR-executor + oneDNN-instruction bug that raises
        # NotImplementedError(ConvertPirAttribute2RuntimeAttribute)
        # at predict-time on real images, regardless of which
        # PP-OCRv5 / PP-OCRv4 detection variant is used. Runtime
        # flags (FLAGS_use_mkldnn=0, FLAGS_enable_pir_in_executor=
        # false) don't sidestep it. paddle 3.2.x runs cleanly with
        # default models. Revisit once paddlepaddle ships a 3.3.x
        # patch or a 3.4 series with the fix.
        self._ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,
        )
        self._lang = lang

    @property
    def is_loaded(self) -> bool:
        return True

    @property
    def model_id(self) -> str:
        # Coarse but stable: backend identifier + language. Sufficient
        # for /healthz consumers; finer model-version provenance can
        # land later if a debug story needs it.
        return f"paddleocr-{self._lang}"

    def ocr(self, image_bytes: bytes) -> list[RawOcrLine]:
        # Lazy imports stay co-located with the engine call so unit
        # tests that touch the Protocol but never instantiate this
        # class don't pay the import cost.
        import numpy as np  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)

        # PaddleOCR.predict returns a list of OCRResult objects (one
        # per input image). Single-image input ⇒ exactly one element.
        results = self._ocr.predict(arr)
        if not results:
            return []
        first = results[0]

        # PaddleOCR 3.x OCRResult exposes .json with detection polygons
        # and recognition outputs. Field shape:
        #   res = first['res']
        #   res['rec_texts']: list[str]
        #   res['rec_scores']: list[float]
        #   res['rec_polys']: list[list[(x,y)]]  -- 4-point bounding boxes
        # Order is top-to-bottom by detection sort; we rely on that
        # for line ordering downstream.
        try:
            res = first.json["res"]
            texts: list[str] = res["rec_texts"]
            scores: list[float] = res["rec_scores"]
            polys = res["rec_polys"]
        except (KeyError, AttributeError, TypeError) as exc:
            log.warning("PaddleOCR result shape unexpected (%s); returning empty", exc)
            return []

        return [
            RawOcrLine(
                text=text,
                confidence=float(score),
                y_offset_px=_poly_y_center(poly),
            )
            for text, score, poly in zip(texts, scores, polys, strict=False)
        ]


def _poly_y_center(poly: Any) -> int:
    """Approx vertical centre of a 4-point polygon.

    Defensive: PaddleOCR returns numpy arrays vs nested lists
    depending on version; we duck-type against a
    `Sequence[Sequence[number]]` shape and let except clauses
    swallow any shape mismatch.
    """
    try:
        ys = [float(point[1]) for point in poly]
        return int(sum(ys) / len(ys)) if ys else 0
    except (TypeError, ValueError, IndexError):
        return 0


def build_paddle_runner_or_stub(
    lang: str,
) -> OcrRunner:  # pragma: no cover  # reason: import-time integration tested via smoke flow
    """Try to build a PaddleRunner; return a stub on any failure.

    Failure modes that should not crash the container at startup:
    - PaddleOCR import error (missing wheel for the runtime's ABI)
    - Network failure on first model download
    - Invalid lang code
    - Out-of-memory during model load

    All of these degrade silently to the unloaded-stub state; /healthz
    reports `model_loaded=false` so consumers see the degradation
    explicitly, the same way the off-classifier sidecar handles a
    missing GGUF.
    """
    try:
        return PaddleRunner(lang=lang)
    except Exception as exc:
        log.warning("PaddleOCR init failed (%s); running as stub", exc)
        from receipt_ocr.main import _UnloadedStub  # noqa: PLC0415

        return _UnloadedStub()
