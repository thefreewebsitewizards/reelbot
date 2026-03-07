"""Extract text from images using pytesseract OCR."""

import subprocess
from pathlib import Path
from loguru import logger


def extract_text_from_images(image_paths: list[Path]) -> str:
    """Extract text from a list of images using tesseract OCR.

    Falls back gracefully if tesseract is not installed.
    """
    if not image_paths:
        return ""

    texts = []
    for i, path in enumerate(image_paths, 1):
        try:
            result = subprocess.run(
                ["tesseract", str(path), "stdout", "--psm", "6"],
                capture_output=True, text=True, timeout=30,
            )
            text = result.stdout.strip()
            if text:
                texts.append(f"[Slide {i}]\n{text}")
                logger.debug(f"OCR slide {i}: {len(text)} chars")
            else:
                texts.append(f"[Slide {i}]\n(no text detected)")
        except FileNotFoundError:
            logger.warning("tesseract not installed, skipping OCR")
            return ""
        except subprocess.TimeoutExpired:
            logger.warning(f"OCR timed out on slide {i}")
            texts.append(f"[Slide {i}]\n(OCR timeout)")

    combined = "\n\n".join(texts)
    logger.info(f"OCR extracted {len(combined)} chars from {len(image_paths)} images")
    return combined
