from __future__ import annotations
from PIL import ImageFilter
import numpy as np
from quality_metrics import load_rgb_image


def extract_image_features(image_bytes: bytes) -> dict:
    image = load_rgb_image(image_bytes)
    gray = np.asarray(image.convert("L"), dtype=np.float32)

    width, height = image.size
    megapixels = (width * height) / 1_000_000.0
    brightness = float(gray.mean())
    contrast = float(gray.std())

    # Edge density gives an explainable spatial complexity estimate.
    gx = np.abs(np.diff(gray, axis=1)).mean() if width > 1 else 0.0
    gy = np.abs(np.diff(gray, axis=0)).mean() if height > 1 else 0.0
    complexity = float(gx + gy)

    # Variance of edge-filtered image as a lightweight sharpness estimate.
    edges = np.asarray(image.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    sharpness = float(edges.var())

    return {
        "width": width,
        "height": height,
        "megapixels": megapixels,
        "original_kb": len(image_bytes) / 1024.0,
        "brightness": brightness,
        "contrast": contrast,
        "complexity": complexity,
        "sharpness": sharpness,
    }
