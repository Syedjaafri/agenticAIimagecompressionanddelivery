from __future__ import annotations
from io import BytesIO
from quality_metrics import calculate_quality_metrics, load_rgb_image

QUALITY_LEVELS = [30, 40, 50, 60, 70, 80, 90]


def compress_jpeg(image_bytes: bytes, quality: int) -> bytes:
    """Compress image to JPEG format at specified quality without downscaling."""
    image = load_rgb_image(image_bytes)
    output = BytesIO()
    image.save(output, format="JPEG", quality=int(quality), optimize=True)
    return output.getvalue()


def transmission_seconds(size_bytes: int, network_mbps: float) -> float:
    """Calculate transmission time in seconds based on bandwidth."""
    return (size_bytes * 8) / (network_mbps * 1_000_000)


def generate_candidates(
    image_bytes: bytes,
    minimum_similarity: float,
    network_mbps: float,
    max_attachment_kb: float,
) -> list[dict]:
    """
    Generate valid compression candidates.
    Strictly discards any quality level where compressed size >= original size.
    Guarantees that all returned candidates achieve positive reduction (> 0%).
    """
    original_size = len(image_bytes)
    candidates = []

    for quality in QUALITY_LEVELS:
        compressed = compress_jpeg(image_bytes, quality)
        compressed_size = len(compressed)

        # STRICT FILTER: Never accept any quality that increases file size
        if compressed_size >= original_size:
            continue

        size_kb = compressed_size / 1024.0
        reduction_percent = ((original_size - compressed_size) / original_size) * 100.0
        metrics = calculate_quality_metrics(image_bytes, compressed)

        item = {
            "quality": quality,
            "image_bytes": compressed,
            "size_kb": size_kb,
            "reduction_percent": reduction_percent,
            "similarity": metrics["similarity"],
            "psnr_db": metrics["psnr_db"],
            "transmission_seconds": transmission_seconds(compressed_size, network_mbps),
            "quality_ok": metrics["similarity"] >= minimum_similarity,
            "attachment_ok": size_kb <= max_attachment_kb,
        }
        item["acceptable"] = item["quality_ok"] and item["attachment_ok"]
        candidates.append(item)

    # Sort strictly by quality ascending so metrics progress predictably in UI
    candidates.sort(key=lambda c: c["quality"])
    return candidates


def choose_best_candidate(candidates: list[dict]) -> dict | None:
    """
    Select the optimal candidate:
    The candidate that meets both perceptual quality and size constraints
    while achieving the highest bandwidth and storage efficiency (smallest size).
    """
    acceptable = [c for c in candidates if c["acceptable"]]
    if not acceptable:
        return None
    return min(acceptable, key=lambda c: c["size_kb"])
