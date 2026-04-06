"""Inference service: video frame extraction, Mask R-CNN segmentation, video composition.

Optimized for high-end GPUs (e.g. RTX 5090) with:
- AMP (float16) for tensor-core throughput
- Pipelined I/O: decode, GPU forward, and disk writes overlap via ThreadPoolExecutor
- Pinned-memory + non_blocking transfers for fast CPU->GPU DMA
- Large batch sizes to saturate GPU compute

Note: torch.compile is NOT used here. Mask R-CNN's dynamic-shape outputs (varying
proposal counts, Tensor.item() calls in post-processing) cause graph breaks and
recompilation storms that make compiled mode ~10x slower than eager.
"""

from __future__ import annotations

import os
from concurrent.futures import Future, ThreadPoolExecutor
from glob import glob
from typing import Generator, Optional

import cv2
import numpy as np
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_use_amp = device.type == "cuda"

_model: Optional[torch.nn.Module] = None
model_status: str = "not_loaded"
model_status_detail: str = ""


def load_model(model_path: str) -> None:
    global _model, model_status, model_status_detail
    model_status = "loading"
    model_status_detail = "Loading model weights from disk..."
    _model = torch.load(model_path, map_location=device, weights_only=False)
    _model.eval()
    model_status_detail = "Transferring model to GPU..."
    _model.to(device)
    model_status = "loaded"
    model_status_detail = "Model loaded, waiting for warmup..."


def warmup_model() -> None:
    """Run a single warm-up forward pass to pre-allocate GPU memory and warm cuDNN."""
    global model_status, model_status_detail
    if _model is None or device.type != "cuda":
        model_status = "ready"
        model_status_detail = ""
        return

    model_status = "warming_up"
    model_status_detail = "Warm-up pass (cuDNN autotuning)..."
    print("[inference] Warmup: running warm-up batch...")
    dummy = [torch.randn(3, 296, 472, device=device) for _ in range(16)]
    with torch.inference_mode(), torch.amp.autocast("cuda"):
        try:
            _model(dummy)
        except Exception:
            pass
    torch.cuda.synchronize()
    del dummy
    torch.cuda.empty_cache()

    model_status = "ready"
    model_status_detail = ""
    print("[inference] Warmup complete — model ready")


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


# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Pipeline stage functions (run in ThreadPoolExecutor)
# ---------------------------------------------------------------------------

def _decode_batch(paths: list[str]) -> tuple[list[np.ndarray], list[torch.Tensor]]:
    """Stage 1: decode images from disk and build pinned-memory tensors."""
    images_rgb: list[np.ndarray] = []
    tensors: list[torch.Tensor] = []
    for p in paths:
        bgr = cv2.imread(p)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        images_rgb.append(rgb)
        t = torch.from_numpy(rgb.transpose(2, 0, 1).copy()).float().div_(255.0)
        if device.type == "cuda":
            t = t.pin_memory()
        tensors.append(t)
    return images_rgb, tensors


def _postprocess_and_write(
    batch_indices: list[int],
    images_rgb: list[np.ndarray],
    predictions: list[dict],
    confidence: float,
    overlays_dir: str,
    masks_dir: str,
) -> int:
    """Stage 3: create overlays, write overlay/mask files. Returns error count."""
    errors = 0
    for j, pred in enumerate(predictions):
        idx = batch_indices[j]
        try:
            m, _, _ = _process_prediction(pred, confidence)
            overlay, mask = _create_overlay(images_rgb[j], m)
            cv2.imwrite(
                os.path.join(overlays_dir, f"overlay_{idx:04d}.jpg"),
                cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR),
            )
            if mask is not None:
                cv2.imwrite(os.path.join(masks_dir, f"mask_{idx:04d}.tiff"), mask)
                cv2.imwrite(os.path.join(masks_dir, f"mask_{idx:04d}.png"), mask)
        except Exception as e:
            errors += 1
            print(f"[frame {idx}] skipped: {e}")
            if j < len(images_rgb) and images_rgb[j] is not None:
                cv2.imwrite(
                    os.path.join(overlays_dir, f"overlay_{idx:04d}.jpg"),
                    cv2.cvtColor(images_rgb[j], cv2.COLOR_RGB2BGR),
                )
    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def segment_frame(
    img_path: str, model: torch.nn.Module, confidence: float = 0.9
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """Segment a single frame. Returns (overlay_image, rgb_mask_or_None)."""
    img_bgr = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    t = torch.from_numpy(img_rgb.transpose(2, 0, 1).copy()).float().div_(255.0)
    if device.type == "cuda":
        t = t.pin_memory()
    tensor = t.to(device, non_blocking=True)

    with torch.inference_mode():
        if _use_amp:
            with torch.amp.autocast("cuda"):
                pred = model([tensor])
        else:
            pred = model([tensor])

    masks, boxes, labels = _process_prediction(pred[0], confidence)
    return _create_overlay(img_rgb, masks)


def run_inference(
    frames_dir: str,
    output_dir: str,
    confidence: float = 0.9,
    batch_size: int = 16,
) -> Generator[tuple[int, int], None, None]:
    """Run pipelined batched inference on all frames.

    Three-stage pipeline overlapping CPU I/O with GPU compute:
      Stage 1 (thread pool): decode next batch from disk + build tensors
      Stage 2 (main thread): GPU forward pass on current batch (AMP float16)
      Stage 3 (thread pool): post-process + write results for previous batch

    Yields (current_frame, total_frames) for progress reporting.
    """
    model = get_model()
    masks_dir = os.path.join(output_dir, "masks")
    overlays_dir = os.path.join(output_dir, "overlays")
    os.makedirs(masks_dir, exist_ok=True)
    os.makedirs(overlays_dir, exist_ok=True)

    frames = sorted(glob(os.path.join(frames_dir, "*.jpg")))
    total = len(frames)
    if total == 0:
        return

    batches: list[list[str]] = []
    for i in range(0, total, batch_size):
        batches.append(frames[i : i + batch_size])
    num_batches = len(batches)

    errors = 0
    write_future: Optional[Future] = None
    progress_count = 0

    with ThreadPoolExecutor(max_workers=4) as pool, torch.inference_mode():
        decode_future = pool.submit(_decode_batch, batches[0])

        for b in range(num_batches):
            images_rgb, tensors = decode_future.result()

            if b + 1 < num_batches:
                decode_future = pool.submit(_decode_batch, batches[b + 1])

            gpu_tensors = [t.to(device, non_blocking=True) for t in tensors]
            if device.type == "cuda":
                torch.cuda.synchronize()

            try:
                if _use_amp:
                    with torch.amp.autocast("cuda"):
                        predictions = model(gpu_tensors)
                else:
                    predictions = model(gpu_tensors)
            except Exception as e:
                batch_start = b * batch_size
                for j in range(len(batches[b])):
                    idx = batch_start + j
                    errors += 1
                    print(f"[frame {idx}] batch failed: {e}")
                    if j < len(images_rgb) and images_rgb[j] is not None:
                        cv2.imwrite(
                            os.path.join(overlays_dir, f"overlay_{idx:04d}.jpg"),
                            cv2.cvtColor(images_rgb[j], cv2.COLOR_RGB2BGR),
                        )
                    progress_count += 1
                    yield (progress_count, total)
                del gpu_tensors
                continue

            cpu_preds = [
                {k: v.detach().cpu() for k, v in p.items()} for p in predictions
            ]
            del gpu_tensors, predictions

            if write_future is not None:
                errs = write_future.result()
                errors += errs

            batch_start = b * batch_size
            batch_indices = list(range(batch_start, batch_start + len(batches[b])))
            write_future = pool.submit(
                _postprocess_and_write,
                batch_indices,
                images_rgb,
                cpu_preds,
                confidence,
                overlays_dir,
                masks_dir,
            )

            progress_count += len(batches[b])
            yield (progress_count, total)

        if write_future is not None:
            errs = write_future.result()
            errors += errs

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
