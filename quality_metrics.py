from __future__ import annotations
from io import BytesIO
import math
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def load_rgb_image(image_bytes: bytes) -> Image.Image:
    """Load image bytes into a clean RGB PIL Image, properly handling transparency."""
    image = Image.open(BytesIO(image_bytes))
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        image = Image.alpha_composite(background, rgba).convert("RGB")
    else:
        image = image.convert("RGB")
    return image


def calculate_quality_metrics(original_bytes: bytes, compressed_bytes: bytes) -> dict:
    """Calculate SSIM, PSNR, and MSE between original and compressed image bytes."""
    orig_img = load_rgb_image(original_bytes)
    comp_img = load_rgb_image(compressed_bytes)

    # Ensure identical dimensions if needed
    if comp_img.size != orig_img.size:
        comp_img = comp_img.resize(orig_img.size, Image.Resampling.LANCZOS)

    orig_arr = np.asarray(orig_img, dtype=np.uint8)
    comp_arr = np.asarray(comp_img, dtype=np.uint8)

    # Determine window size safely for small images
    min_dim = min(orig_arr.shape[0], orig_arr.shape[1])
    win_size = min(7, min_dim)
    if win_size % 2 == 0:
        win_size -= 1
    win_size = max(3, win_size)

    # Multichannel SSIM across RGB
    similarity = float(structural_similarity(
        orig_arr,
        comp_arr,
        channel_axis=2,
        win_size=win_size,
        data_range=255,
    ))
    similarity = float(np.clip(similarity, 0.0, 1.0))

    # MSE and PSNR calculation
    mse = float(np.mean((orig_arr.astype(np.float64) - comp_arr.astype(np.float64)) ** 2))
    if mse == 0.0:
        psnr = 99.0
    else:
        psnr = float(20.0 * math.log10(255.0 / math.sqrt(mse)))

    return {
        "similarity": similarity,
        "psnr_db": psnr,
        "mse": mse,
    }
