from __future__ import annotations
from io import BytesIO
import math
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def _rgb_array(image_bytes: bytes, size=None) -> np.ndarray:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    if size is not None and image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.uint8)


def calculate_quality_metrics(original_bytes: bytes, compressed_bytes: bytes) -> dict:
    original_image = Image.open(BytesIO(original_bytes)).convert("RGB")
    original = np.asarray(original_image, dtype=np.uint8)
    compressed = _rgb_array(compressed_bytes, original_image.size)

    similarity = float(structural_similarity(original, compressed, channel_axis=2, data_range=255))
    mse = float(np.mean((original.astype(np.float32) - compressed.astype(np.float32)) ** 2))
    psnr = float("inf") if mse == 0 else 20 * math.log10(255.0 / math.sqrt(mse))
    return {"similarity": similarity, "psnr_db": psnr, "mse": mse}
