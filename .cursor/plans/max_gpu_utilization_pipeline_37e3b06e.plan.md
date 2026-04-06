---
name: Max GPU utilization pipeline
overview: Restructure inference.py into a 3-stage pipeline that overlaps CPU I/O, GPU inference, and CPU post-processing, plus increase batch size and add torch.compile and fp16 to maximize 5090 throughput.
todos:
  - id: torch-compile-amp
    content: Add torch.compile at model load + AMP autocast in inference loop
    status: completed
  - id: batch-size
    content: Increase default batch_size from 4 to 16
    status: completed
  - id: pipeline
    content: Implement 3-stage pipeline with ThreadPoolExecutor (decode/GPU/write overlap)
    status: completed
  - id: pin-memory
    content: Use non_blocking=True and pinned memory for CPU->GPU transfers
    status: completed
isProject: false
---

# Maximize 5090 GPU Utilization

The current code is **GPU-bound by CPU bottlenecks**: the GPU sits idle while images are decoded, tensors are built, overlays are created, and files are written. On a 5090, the model forward pass for 4 small (~296x472) images is probably ~10-20ms, but CPU work per batch is ~50-100ms. The GPU is idle 80%+ of the time.

## Changes (all in `inference.py`)

### 1. Increase batch size: 4 -> 16

With 32GB VRAM and small input images (~296x472), the 5090 can easily handle 16+ images per batch. Mask R-CNN on these tiny images uses maybe ~200-400MB per image in the batch. 16 images = ~6GB peak, well within 32GB.

### 2. `torch.compile()` the model

PyTorch 2.x `torch.compile` with the default `inductor` backend fuses GPU kernels and eliminates Python overhead. On a 5090 (Ada/Blackwell), this can give 1.3-2x speedup on the forward pass itself. Applied once at model load time:

```python
def load_model(model_path: str) -> None:
    global _model
    _model = torch.load(model_path, map_location=device, weights_only=False)
    _model.eval()
    _model.to(device)
    if device.type == "cuda":
        _model = torch.compile(_model, mode="reduce-overhead")
```

The first batch will be slower (compilation), all subsequent batches much faster.

### 3. FP16 / AMP (Automatic Mixed Precision)

Run the model in float16. The 5090 has massive FP16 tensor cores. This roughly doubles throughput and halves memory per batch:

```python
with torch.inference_mode(), torch.amp.autocast("cuda"):
    predictions = model(tensors)
```

### 4. Pipeline: overlap CPU I/O with GPU inference

This is the big architectural change. Instead of the current sequential flow:

```
[decode batch] -> [GPU forward] -> [post-process] -> [write files] -> repeat
```

Use a **3-stage pipeline** with `concurrent.futures.ThreadPoolExecutor`:

- **Stage 1 (IO threads):** Decode the NEXT batch of images from disk + convert to tensors
- **Stage 2 (GPU):** Run model on the CURRENT batch
- **Stage 3 (IO threads):** Write overlays/masks for the PREVIOUS batch

All three stages run **simultaneously**. The GPU never waits for disk I/O.

```python
from concurrent.futures import ThreadPoolExecutor

def _decode_batch(paths):
    """Runs in thread pool -- decode images and build tensors."""
    images_rgb = []
    tensors = []
    for p in paths:
        bgr = cv2.imread(p)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        images_rgb.append(rgb)
        tensors.append(_to_tensor(rgb))
    stacked = [t.to(device, non_blocking=True) for t in tensors]
    return images_rgb, stacked

def _write_results(results, overlays_dir, masks_dir):
    """Runs in thread pool -- create overlays and write all files."""
    for idx, img_rgb, pred, confidence in results:
        masks, _, _ = _process_prediction(pred, confidence)
        overlay, mask = _create_overlay(img_rgb, masks)
        cv2.imwrite(os.path.join(overlays_dir, f"overlay_{idx:04d}.jpg"),
                     cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
        if mask is not None:
            cv2.imwrite(os.path.join(masks_dir, f"mask_{idx:04d}.tiff"), mask)
            cv2.imwrite(os.path.join(masks_dir, f"mask_{idx:04d}.png"), mask)
```

Then the main loop becomes:

```python
with ThreadPoolExecutor(max_workers=4) as pool:
    # Pre-submit first batch decode
    next_future = pool.submit(_decode_batch, batch_paths[0])

    for batch_idx in range(num_batches):
        # Wait for current batch decode
        images_rgb, tensors = next_future.result()

        # Submit NEXT batch decode (overlaps with GPU)
        if batch_idx + 1 < num_batches:
            next_future = pool.submit(_decode_batch, batch_paths[batch_idx+1])

        # GPU forward (while next decode + prev write run in parallel)
        predictions = model(tensors)

        # Submit write for THIS batch (overlaps with next GPU forward)
        pool.submit(_write_results, ...)

        yield progress
```

### 5. Use `non_blocking=True` for CPU->GPU transfer

When moving tensors to GPU, `tensor.to(device, non_blocking=True)` allows the CPU to continue while the transfer happens over PCIe asynchronously. Combined with CUDA streams, this overlaps data transfer with computation.

### 6. Pin memory for faster CPU->GPU transfer

Using `torch.from_numpy()` on pinned memory arrays enables faster DMA transfers to the GPU:

```python
tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0)
tensor = tensor.pin_memory().to(device, non_blocking=True)
```

## Expected speedup


| Optimization              | Speedup estimate                   |
| ------------------------- | ---------------------------------- |
| Batch 4 -> 16             | ~1.5-2x (better GPU saturation)    |
| torch.compile             | ~1.3-2x on forward pass            |
| FP16 / AMP                | ~1.5-2x on forward pass, half VRAM |
| Pipeline overlap          | ~2-3x (GPU never waits for I/O)    |
| non_blocking + pin_memory | ~1.1-1.2x                          |
| **Combined**              | **~4-8x faster than current code** |


For 101 frames at ~296x472, total inference could drop from several seconds to under a second on a 5090.

## Files to modify

- [web/backend/services/inference.py](bitsXlaMarato/web/backend/services/inference.py): All changes above

