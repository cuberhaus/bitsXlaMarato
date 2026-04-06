# GPU Inference Pipeline — Technical Notes

This document describes the performance optimizations applied to the inference pipeline and the problems they solve.

## Problem: GPU underutilization

The original code processed frames **one at a time**: decode image, run model, create overlay, write files, repeat. On a high-end GPU (e.g. RTX 5090), the model forward pass for a small 296x472 image takes ~10-20ms, but the surrounding CPU work (image decode, file I/O, overlay creation) takes ~50-100ms. The GPU was idle **80%+ of the time**.

**Solution — pipelined batched inference:**

| Optimization | What it does | Speedup |
|---|---|---|
| Batch size 16 | Sends 16 frames to the GPU backbone in a single forward pass | ~1.5-2x |
| FP16 / AMP (`torch.amp.autocast`) | Runs in half-precision to leverage GPU tensor cores | ~1.2x |
| Pipelined I/O (`ThreadPoolExecutor`) | Overlaps disk decode, GPU forward, and disk write | ~2-3x |
| Pinned memory + `non_blocking` transfer | DMA transfers that overlap with GPU compute | ~1.1-1.2x |

Combined result: **~2.5x faster** inference (101 frames in ~5s on RTX 5090 vs ~12s before).

### Why not `torch.compile`?

Mask R-CNN is **not compatible** with `torch.compile(mode="reduce-overhead")`. Testing showed it made inference **~10x slower** due to:

- **Graph breaks**: `Tensor.item()` calls in torchvision's post-processing (`paste_masks_in_image`, `roi_heads`) force the compiler to break the graph into many small subgraphs.
- **Dynamic shapes**: The Region Proposal Network produces varying numbers of proposals per image, causing constant CUDA graph re-recording (9+ distinct sizes observed).
- **Recompilation storms**: `roi_align` and `MultiScaleRoIAlign.forward` hit the recompilation limit (8) on every batch.

This is a known limitation of detection models. `torch.compile` works well with fixed-shape models (classifiers, transformers with fixed sequence lengths) but not with models whose output tensor counts and shapes vary per input.

### Pipeline architecture

The inference loop uses a 3-stage pipeline so the GPU never waits for disk I/O:

```
  Thread pool          Main thread          Thread pool
┌─────────────┐   ┌─────────────────┐   ┌──────────────────┐
│ Decode batch │   │ GPU forward     │   │ Post-process +   │
│ N+1 from     │   │ pass on batch N │   │ write results    │
│ disk + build │   │ (AMP float16)   │   │ for batch N-1    │
│ tensors      │   │                 │   │                  │
└─────────────┘   └─────────────────┘   └──────────────────┘
       ↓                   ↓                      ↓
   All three stages run simultaneously per iteration
```

Key implementation details (`web/backend/services/inference.py`):

- Images are decoded **once** with `cv2.imread` and reused for both tensor conversion and overlay creation (previously decoded twice — PIL + cv2).
- `torch.inference_mode()` wraps the entire loop, disabling autograd tracking.
- Tensors use `pin_memory()` + `.to(device, non_blocking=True)` for async DMA transfers.
- GPU predictions are moved to CPU (`detach().cpu()`) immediately after each batch to free VRAM before the next batch.

## Problem: first video slower than subsequent ones

The very first inference after a cold start can be slower because cuDNN needs to auto-tune convolution algorithms for the specific tensor shapes it encounters. We run a single warm-up batch (16 frames at the real image dimensions) at server startup to force this tuning ahead of time:

```python
def warmup_model():
    dummy = [torch.randn(3, 296, 472, device=device) for _ in range(16)]
    with torch.inference_mode(), torch.amp.autocast("cuda"):
        _model(dummy)
    torch.cuda.synchronize()
    del dummy
    torch.cuda.empty_cache()
```

This ensures cuDNN selects optimal algorithms before any user-facing inference happens.

## Problem: server blocked during mesh generation

Mesh generation (both original meshlib and improved marching cubes) ran **synchronously** inside async route handlers. While a mesh was generating (10-30 seconds), the entire FastAPI event loop was blocked — no other API calls (status polling, frame serving) could be processed.

**Solution:** Offloaded to `asyncio.to_thread()` so mesh generation runs in a thread pool while the event loop stays responsive.

```python
@app.post("/api/jobs/{job_id}/mesh")
async def trigger_mesh(job_id: str):
    stl_path = await asyncio.to_thread(generate_mesh, str(masks_dir))
    return {"stl_path": str(stl_path), "status": "ok"}
```

## Problem: memory spike on video upload

`await file.read()` loaded the **entire video file into memory** before writing to disk. For large videos this caused unnecessary memory spikes.

**Solution:** Streaming chunked upload — reads 1MB at a time, keeping peak memory constant regardless of video size.

```python
with open(video_path, "wb") as f:
    while chunk := await file.read(1024 * 1024):
        f.write(chunk)
```

## Problem: repeated TIFF-to-PNG conversion

The `/masks/{n}` endpoint converted TIFF masks to PNG **on every request** using PIL. This added ~15-30ms per request for no reason on repeated access.

**Solution:** During inference, a `.png` is saved alongside each `.tiff`. The endpoint serves the cached PNG directly via `FileResponse` (~1ms). Falls back to TIFF conversion for older jobs, caching the result on first access.
