"""Inference service: video frame extraction, Mask R-CNN segmentation, video composition."""

from __future__ import annotations

import os
import shutil
from glob import glob
from pathlib import Path
from typing import Generator, Optional

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_model: Optional[torch.nn.Module] = None


def load_model(model_path: str) -> None:
    global _model
    _model = torch.load(model_path, map_location=device, weights_only=False)
    _model.eval()
    _model.to(device)


def get_model() -> torch.nn.Module:
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    return _model


def extract_frames(
    video_path: str,
    output_dir: str,
    crop_roi: Optional[tuple[int, int, int, int]] = None,
) -> int:
    """Extract frames from video, optionally cropping. Returns frame count."""
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    count = 0

    while True:
        success, frame = cap.read()
        if not success:
            break
        if crop_roi:
            y1, y2, x1, x2 = crop_roi
            frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(os.path.join(output_dir, f"frame_{count:04d}.jpg"), gray)
        count += 1

    cap.release()
    return count


def _get_coloured_mask(mask: np.ndarray) -> np.ndarray:
    r = np.zeros_like(mask, dtype=np.uint8)
    g = np.zeros_like(mask, dtype=np.uint8)
    b = np.zeros_like(mask, dtype=np.uint8)
    r[mask == 1], g[mask == 1], b[mask == 1] = 0, 0, 255
    return np.stack([r, g, b], axis=2)


def _get_prediction(
    img_path: str, confidence: float, model: torch.nn.Module
) -> tuple[np.ndarray, np.ndarray, list]:
    img = Image.open(img_path)
    transform = T.Compose([T.ToTensor()])
    img_tensor = transform(img).to(device)
    pred = model([img_tensor])

    scores = pred[0]["scores"].detach().cpu().numpy().tolist()
    try:
        pred_t = [i for i, x in enumerate(scores) if x > confidence][-1]
    except IndexError:
        return np.array([]), np.array([]), []

    masks = (pred[0]["masks"] > 0.5).squeeze().detach().cpu().numpy()
    labels = pred[0]["labels"].cpu().numpy().tolist()
    boxes = pred[0]["boxes"].detach().cpu().numpy().tolist()

    masks = masks[: pred_t + 1]
    boxes = boxes[: pred_t + 1]
    labels = labels[: pred_t + 1]

    if masks.ndim == 2:
        masks = masks[np.newaxis, ...]

    if len(masks) == 0:
        return np.array([]), np.array([]), []

    return masks, np.array(boxes), labels


def segment_frame(
    img_path: str, model: torch.nn.Module, confidence: float = 0.9
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """Segment a single frame. Returns (overlay_image, rgb_mask_or_None)."""
    masks, boxes, labels = _get_prediction(img_path, confidence, model)
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    rgb_mask = None

    for i in range(len(masks)):
        rgb_mask = _get_coloured_mask(masks[i])
        if rgb_mask.shape[:2] != img.shape[:2]:
            rgb_mask = cv2.resize(rgb_mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
        img = cv2.addWeighted(img, 1, rgb_mask, 0.5, 0)

    return img, rgb_mask


def run_inference(
    frames_dir: str,
    output_dir: str,
    confidence: float = 0.9,
) -> Generator[tuple[int, int], None, None]:
    """Run inference on all frames. Yields (current, total) for progress."""
    model = get_model()
    masks_dir = os.path.join(output_dir, "masks")
    overlays_dir = os.path.join(output_dir, "overlays")
    os.makedirs(masks_dir, exist_ok=True)
    os.makedirs(overlays_dir, exist_ok=True)

    frames = sorted(glob(os.path.join(frames_dir, "*.jpg")))
    total = len(frames)

    errors = 0
    for i, frame_path in enumerate(frames):
        try:
            overlay, mask = segment_frame(frame_path, model, confidence)
            cv2.imwrite(
                os.path.join(overlays_dir, f"overlay_{i:04d}.jpg"),
                cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR),
            )
            if mask is not None:
                cv2.imwrite(os.path.join(masks_dir, f"mask_{i:04d}.tiff"), mask)
        except Exception as e:
            errors += 1
            print(f"[frame {i}] skipped: {e}")
            raw = cv2.imread(frame_path)
            if raw is not None:
                cv2.imwrite(os.path.join(overlays_dir, f"overlay_{i:04d}.jpg"), raw)
        yield (i + 1, total)

    if errors:
        print(f"Inference done with {errors}/{total} frame(s) skipped due to errors.")


def compose_video(frames_dir: str, output_path: str, fps: int = 15) -> None:
    """Compose overlay frames into an AVI video."""
    frames = sorted(glob(os.path.join(frames_dir, "*.jpg")))
    if not frames:
        return

    first = cv2.imread(frames[0])
    h, w = first.shape[:2]
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"DIVX"), fps, (w, h))

    for f in frames:
        writer.write(cv2.imread(f))
    writer.release()
