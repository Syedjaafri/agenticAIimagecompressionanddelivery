from __future__ import annotations
from io import BytesIO
from PIL import Image
from quality_metrics import calculate_quality_metrics

QUALITY_LEVELS = [30, 40, 50, 60, 70, 80, 90]


def compress_jpeg(image_bytes: bytes, quality: int, scale: float = 1.0) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    if scale < 1.0:
        new_w = max(1, int(image.width * scale))
        new_h = max(1, int(image.height * scale))
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, format="JPEG", quality=int(quality), optimize=True)
    return output.getvalue()


def transmission_seconds(size_bytes: int, network_mbps: float) -> float:
    return (size_bytes * 8) / (network_mbps * 1_000_000)


def generate_candidates(
    image_bytes: bytes,
    minimum_similarity: float,
    network_mbps: float,
    max_attachment_kb: float,
) -> list[dict]:
    original_size = len(image_bytes)
    candidates = []
    
    # Try full resolution first, then downscale if needed to fit under size limit
    scales = [1.0, 0.85, 0.70, 0.50]
    for scale in scales:
        for quality in QUALITY_LEVELS:
            compressed = compress_jpeg(image_bytes, quality, scale)
            metrics = calculate_quality_metrics(image_bytes, compressed)
            size_kb = len(compressed) / 1024
            item = {
                "quality": quality,
                "scale": scale,
                "image_bytes": compressed,
                "size_kb": size_kb,
                "reduction_percent": ((original_size - len(compressed)) / original_size) * 100,
                "similarity": metrics["similarity"],
                "psnr_db": metrics["psnr_db"],
                "transmission_seconds": transmission_seconds(len(compressed), network_mbps),
            }
            item["quality_ok"] = item["similarity"] >= minimum_similarity
            item["attachment_ok"] = size_kb <= max_attachment_kb
            item["acceptable"] = item["quality_ok"] and item["attachment_ok"]
            candidates.append(item)
            
        # If we found at least one acceptable candidate at full scale, no need to downscale
        if any(c["acceptable"] for c in candidates if c["scale"] == scale):
            break

    return candidates


def choose_best_candidate(candidates: list[dict]) -> dict | None:
    acceptable = [c for c in candidates if c["acceptable"]]
    return min(acceptable, key=lambda c: c["size_kb"]) if acceptable else None

