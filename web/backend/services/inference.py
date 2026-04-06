"""Inference service: video frame extraction, Mask R-CNN segmentation, video composition."""

from __future__ import annotations

import os
from glob import glob
from typing import Generator, Optional

import cv2
import numpy as np
import torch
import torchvision.transforms as T

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_model: Optional[torch.nn.Module] = None
_to_tensor = T.ToTensor()


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


def _process_prediction(
    pred: dict, confidence: float
) -> tuple[np.ndarray, np.ndarray, list]:
    """Extract masks, boxes, labels from a single model prediction dict."""
    scores = pred["scores"].detach().cpu().numpy().tolist()
    try:
        pred_t = [i for i, x in enumerate(scores) if x > confidence][-1]
    except IndexError:
        return np.array([]), np.array([]), []

    masks = (pred["masks"] > 0.5).squeeze().detach().cpu().numpy()
    labels = pred["labels"].cpu().numpy().tolist()
    boxes = pred["boxes"].detach().cpu().numpy().tolist()

    masks = masks[: pred_t + 1]
    boxes = boxes[: pred_t + 1]
    labels = labels[: pred_t + 1]

    if masks.ndim == 2:
        masks = masks[np.newaxis, ...]

    if len(masks) == 0:
        return np.array([]), np.array([]), []

    return masks, np.array(boxes), labels


def _create_overlay(
    img_rgb: np.ndarray, masks: np.ndarray
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """Create overlay image from RGB image and predicted masks."""
    rgb_mask = None
    overlay = img_rgb.copy()
    for i in range(len(masks)):
        rgb_mask = _get_coloured_mask(masks[i])
        if rgb_mask.shape[:2] != overlay.shape[:2]:
            rgb_mask = cv2.resize(
                rgb_mask,
                (overlay.shape[1], overlay.shape[0]),
                interpolation=cv2.INTER_NEAREST,
            )
        overlay = cv2.addWeighted(overlay, 1, rgb_mask, 0.5, 0)
    return overlay, rgb_mask


def segment_frame(
    img_path: str, model: torch.nn.Module, confidence: float = 0.9
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """Segment a single frame. Returns (overlay_image, rgb_mask_or_None)."""
    img_bgr = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    tensor = _to_tensor(img_rgb).to(device)

    with torch.inference_mode():
        pred = model([tensor])

    masks, boxes, labels = _process_prediction(pred[0], confidence)
    return _create_overlay(img_rgb, masks)


def run_inference(
    frames_dir: str,
    output_dir: str,
    confidence: float = 0.9,
    batch_size: int = 4,
) -> Generator[tuple[int, int], None, None]:
    """Run batched inference on all frames. Yields (current, total) for progress.

    Processes frames in batches for better GPU throughput. Each image is decoded
    once (cv2) and reused for both tensor conversion and overlay creation.
    """
    model = get_model()
    masks_dir = os.path.join(output_dir, "masks")
    overlays_dir = os.path.join(output_dir, "overlays")
    os.makedirs(masks_dir, exist_ok=True)
    os.makedirs(overlays_dir, exist_ok=True)

    frames = sorted(glob(os.path.join(frames_dir, "*.jpg")))
    total = len(frames)
    errors = 0

    with torch.inference_mode():
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_paths = frames[batch_start:batch_end]

            images_bgr = []
            images_rgb = []
            tensors = []
            for path in batch_paths:
                img_bgr = cv2.imread(path)
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                images_bgr.append(img_bgr)
                images_rgb.append(img_rgb)
                tensors.append(_to_tensor(img_rgb).to(device))

            try:
                predictions = model(tensors)
            except Exception as e:
                for j, path in enumerate(batch_paths):
                    idx = batch_start + j
                    errors += 1
                    print(f"[frame {idx}] batch failed: {e}")
                    if j < len(images_bgr) and images_bgr[j] is not None:
                        cv2.imwrite(
                            os.path.join(overlays_dir, f"overlay_{idx:04d}.jpg"),
                            images_bgr[j],
                        )
                    yield (idx + 1, total)
                del tensors
                continue

            for j, pred in enumerate(predictions):
                idx = batch_start + j
                try:
                    masks, boxes, labels = _process_prediction(pred, confidence)
                    overlay, mask = _create_overlay(images_rgb[j], masks)
                    cv2.imwrite(
                        os.path.join(overlays_dir, f"overlay_{idx:04d}.jpg"),
                        cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR),
                    )
                    if mask is not None:
                        cv2.imwrite(
                            os.path.join(masks_dir, f"mask_{idx:04d}.tiff"), mask
                        )
                        cv2.imwrite(
                            os.path.join(masks_dir, f"mask_{idx:04d}.png"), mask
                        )
                except Exception as e:
                    errors += 1
                    print(f"[frame {idx}] skipped: {e}")
                    if j < len(images_bgr) and images_bgr[j] is not None:
                        cv2.imwrite(
                            os.path.join(overlays_dir, f"overlay_{idx:04d}.jpg"),
                            images_bgr[j],
                        )
                yield (idx + 1, total)

            del tensors, predictions

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
