from __future__ import annotations
from io import BytesIO
from PIL import Image, ImageFilter
import numpy as np


def load_rgb(image_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(image_bytes)).convert("RGB")


def extract_image_features(image_bytes: bytes) -> dict:
    image = load_rgb(image_bytes)
    arr = np.asarray(image, dtype=np.float32)
    gray = np.asarray(image.convert("L"), dtype=np.float32)

    width, height = image.size
    megapixels = (width * height) / 1_000_000
    brightness = float(gray.mean())
    contrast = float(gray.std())

    # Edge density gives a simple, explainable complexity estimate.
    gx = np.abs(np.diff(gray, axis=1)).mean() if width > 1 else 0.0
    gy = np.abs(np.diff(gray, axis=0)).mean() if height > 1 else 0.0
    complexity = float(gx + gy)

    # Variance of an edge-enhanced image is used as a lightweight sharpness estimate.
    edges = np.asarray(image.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    sharpness = float(edges.var())

    return {
        "width": width,
        "height": height,
        "megapixels": megapixels,
        "original_kb": len(image_bytes) / 1024,
        "brightness": brightness,
        "contrast": contrast,
        "complexity": complexity,
        "sharpness": sharpness,
    }
