"""Diameter measurement service: compute aorta diameter from a mask frame."""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np


def measure_diameter(
    mask_path: str,
    pixel_scale: float = 0.03378,
) -> dict:
    """Measure the maximum vertical extent of the aorta in a mask image.

    Args:
        mask_path: Path to mask TIFF file.
        pixel_scale: cm per pixel calibration factor.

    Returns:
        Dict with diameter_cm, diameter_px, bounding_rect, measurement_line.
    """
    mask = cv2.imread(mask_path)
    if mask is None:
        return {"error": "Could not read mask file"}

    gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    if not contours:
        return {"error": "No contours found in mask"}

    longest_contour = None
    longest_distance = 0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h > longest_distance:
            longest_contour = contour
            longest_distance = h

    x, y, w, h = cv2.boundingRect(longest_contour)

    return {
        "diameter_px": longest_distance,
        "diameter_cm": round(longest_distance * pixel_scale, 4),
        "bounding_rect": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
        "measurement_line": {
            "y": int(y),
            "x_start": 0,
            "x_end": int(mask.shape[1]),
        },
        "pixel_scale": pixel_scale,
    }
