"""Diameter measurement service: compute aorta diameter from a mask frame."""

from __future__ import annotations

import cv2
import numpy as np


def _load_binary_mask(mask_path: str):
    """Load a mask image and return (binary, raw_image) or an error dict."""
    mask = cv2.imread(mask_path)
    if mask is None:
        return None, None, {"error": "Could not read mask file"}

    gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None, None, {"error": "No contours found in mask"}

    return contours, mask, None


def measure_diameter(
    mask_path: str,
    pixel_scale: float = 0.03378,
) -> dict:
    """Original hackathon measurement: bounding rect height of the tallest contour."""
    contours, mask, err = _load_binary_mask(mask_path)
    if err:
        return err

    longest_contour = None
    longest_distance = 0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h > longest_distance:
            longest_contour = contour
            longest_distance = h

    x, y, w, h = cv2.boundingRect(longest_contour)
    img_h, img_w = mask.shape[:2]
    mid_x = int(x + w / 2)

    return {
        "diameter_px": longest_distance,
        "diameter_cm": round(longest_distance * pixel_scale, 4),
        "bounding_rect": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
        "measurement_line": {
            "x1": mid_x, "y1": int(y),
            "x2": mid_x, "y2": int(y + h),
        },
        "image_size": {"w": img_w, "h": img_h},
        "pixel_scale": pixel_scale,
    }


def measure_diameter_improved(
    mask_path: str,
    pixel_scale: float = 0.03378,
) -> dict:
    """Improved measurement: ellipse minor axis as the diameter value.

    Uses cv2.fitEllipse for a robust, rotation-invariant diameter (minor axis).
    The measurement line spans the full minor axis endpoints.
    """
    contours, mask, err = _load_binary_mask(mask_path)
    if err:
        return err

    contour = max(contours, key=cv2.contourArea)

    if len(contour) < 5:
        return {"error": "Contour too small for measurement"}

    ell = cv2.fitEllipse(contour)
    center, (w_ax, h_ax), angle_deg = ell
    major = float(max(w_ax, h_ax))
    minor = float(min(w_ax, h_ax))

    if w_ax <= h_ax:
        minor_angle_deg = float(angle_deg)
    else:
        minor_angle_deg = float(angle_deg) + 90.0

    minor_rad = np.radians(minor_angle_deg)
    dx = np.cos(minor_rad)
    dy = np.sin(minor_rad)
    cx, cy = float(center[0]), float(center[1])
    half = minor / 2.0

    ellipse_data = {
        "cx": round(cx, 1),
        "cy": round(cy, 1),
        "major": round(major, 1),
        "minor": round(minor, 1),
        "angle": round(float(angle_deg), 1),
    }

    x, y, w, h = cv2.boundingRect(contour)
    img_h, img_w = mask.shape[:2]

    return {
        "diameter_px": round(minor, 1),
        "diameter_cm": round(minor * pixel_scale, 4),
        "bounding_rect": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
        "measurement_line": {
            "x1": int(round(cx + dx * half)), "y1": int(round(cy + dy * half)),
            "x2": int(round(cx - dx * half)), "y2": int(round(cy - dy * half)),
        },
        "ellipse": ellipse_data,
        "image_size": {"w": img_w, "h": img_h},
        "pixel_scale": pixel_scale,
        "method": "ellipse",
    }
