"""FastAPI backend for bitsXlaMarato aorta segmentation web interface."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

try:
    from services.inference import (
        load_model,
        warmup_model,
        extract_frames,
        run_inference,
        compose_video,
        model_status as _unused,
    )
    import services.inference as _inference_mod
    INFERENCE_AVAILABLE = True
except ImportError:
    INFERENCE_AVAILABLE = False
    _inference_mod = None

try:
    from services.mesh import generate_mesh, MESHLIB_AVAILABLE
except ImportError:
    MESHLIB_AVAILABLE = False

try:
    from services.diameter import measure_diameter, measure_diameter_improved
    DIAMETER_AVAILABLE = True
except ImportError:
    DIAMETER_AVAILABLE = False

try:
    from services.mesh_improved import generate_mesh_improved, IMPROVED_MESH_AVAILABLE
except ImportError:
    IMPROVED_MESH_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
JOBS_DIR = Path(__file__).resolve().parent / "jobs"
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "frontend" / "browser"

DEFAULT_MODEL = "maratoNuevo.pt"
DEFAULT_CROP = (84, 380, 54, 526)  # y1, y2, x1, x2

active_model_name: str = DEFAULT_MODEL
jobs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global active_model_name
    model_path = MODELS_DIR / DEFAULT_MODEL
    if INFERENCE_AVAILABLE and model_path.exists() and model_path.stat().st_size > 1000:
        try:
            load_model(str(model_path))
            active_model_name = DEFAULT_MODEL
            print(f"Model loaded from {model_path}")
            thread = threading.Thread(target=warmup_model, daemon=True)
            thread.start()
        except Exception as e:
            print(f"Warning: Failed to load model: {e}")
    else:
        reason = "torch/torchvision not installed" if not INFERENCE_AVAILABLE else f"Model not found at {model_path}"
        print(f"Warning: {reason}. Inference endpoints will fail.")
    JOBS_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(title="bitsXlaMarato - Aorta Segmentation", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_job(job_id: str, video_path: str, confidence: float, crop_roi: Optional[tuple]) -> None:
    """Background thread: run the full inference pipeline for a job."""
    job = jobs[job_id]
    job_dir = JOBS_DIR / job_id
    frames_dir = str(job_dir / "frames")
    output_dir = str(job_dir / "output")

    try:
        job["state"] = "extracting"
        job["message"] = "Extracting frames from video..."
        n_frames = extract_frames(video_path, frames_dir, crop_roi)
        job["total"] = n_frames
        job["message"] = f"Extracted {n_frames} frames"

        job["state"] = "inferring"
        job["progress"] = 0
        for current, total in run_inference(frames_dir, output_dir, confidence):
            job["progress"] = current
            job["total"] = total
            job["message"] = f"Processing frame {current}/{total}"

        job["state"] = "composing"
        job["message"] = "Composing output video..."
        overlays_dir = os.path.join(output_dir, "overlays")
        compose_video(overlays_dir, str(job_dir / "output" / "result.avi"))

        job["state"] = "done"
        job["message"] = "Processing complete"
    except Exception as e:
        job["state"] = "error"
        job["message"] = str(e)


@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    confidence: float = Query(0.9, ge=0.1, le=1.0),
    use_crop: bool = Query(True),
):
    job_id = str(uuid.uuid4())[:8]
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    video_path = str(job_dir / file.filename)
    with open(video_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    if not INFERENCE_AVAILABLE:
        raise HTTPException(500, "Inference unavailable: torch/torchvision not installed")

    crop_roi = DEFAULT_CROP if use_crop else None

    jobs[job_id] = {
        "state": "uploading",
        "progress": 0,
        "total": 0,
        "message": "Upload complete, starting processing...",
        "video_path": video_path,
        "confidence": confidence,
    }

    thread = threading.Thread(
        target=_run_job, args=(job_id, video_path, confidence, crop_roi), daemon=True
    )
    thread.start()

    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/status")
async def job_status_sse(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    def event_stream():
        last_state = None
        last_progress = -1
        while True:
            job = jobs.get(job_id)
            if not job:
                break
            if job["state"] != last_state or job["progress"] != last_progress:
                last_state = job["state"]
                last_progress = job["progress"]
                data = json.dumps({
                    "state": job["state"],
                    "progress": job["progress"],
                    "total": job["total"],
                    "message": job["message"],
                })
                yield f"data: {data}\n\n"
            if job["state"] in ("done", "error"):
                break
            time.sleep(0.3)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/status-poll")
async def job_status_poll(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    return {
        "state": job["state"],
        "progress": job["progress"],
        "total": job["total"],
        "message": job["message"],
    }


@app.get("/api/jobs/{job_id}/frames")
async def list_frames(job_id: str):
    frames_dir = JOBS_DIR / job_id / "frames"
    if not frames_dir.exists():
        raise HTTPException(404, "Frames not found")
    frames = sorted([f.name for f in frames_dir.glob("*.jpg")])
    return {"frames": frames, "count": len(frames)}


@app.get("/api/jobs/{job_id}/frames/{n}")
async def get_frame(job_id: str, n: int):
    frame_path = JOBS_DIR / job_id / "frames" / f"frame_{n:04d}.jpg"
    if not frame_path.exists():
        raise HTTPException(404, "Frame not found")
    return FileResponse(str(frame_path), media_type="image/jpeg")


@app.get("/api/jobs/{job_id}/overlays")
async def list_overlays(job_id: str):
    overlays_dir = JOBS_DIR / job_id / "output" / "overlays"
    if not overlays_dir.exists():
        raise HTTPException(404, "Overlays not found")
    overlays = sorted([f.name for f in overlays_dir.glob("*.jpg")])
    return {"overlays": overlays, "count": len(overlays)}


@app.get("/api/jobs/{job_id}/overlays/{n}")
async def get_overlay(job_id: str, n: int):
    overlay_path = JOBS_DIR / job_id / "output" / "overlays" / f"overlay_{n:04d}.jpg"
    if not overlay_path.exists():
        raise HTTPException(404, "Overlay not found")
    return FileResponse(str(overlay_path), media_type="image/jpeg")


@app.get("/api/jobs/{job_id}/masks/{n}")
async def get_mask(job_id: str, n: int):
    masks_base = JOBS_DIR / job_id / "output" / "masks"
    png_path = masks_base / f"mask_{n:04d}.png"
    if png_path.exists():
        return FileResponse(str(png_path), media_type="image/png")
    tiff_path = masks_base / f"mask_{n:04d}.tiff"
    if not tiff_path.exists():
        raise HTTPException(404, "Mask not found")
    from io import BytesIO
    from PIL import Image as PILImage
    img = PILImage.open(tiff_path)
    buf = BytesIO()
    img.save(buf, format="PNG")
    with open(str(png_path), "wb") as f:
        f.write(buf.getvalue())
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/api/jobs/{job_id}/video")
async def get_video(job_id: str):
    video_path = JOBS_DIR / job_id / "output" / "result.avi"
    if not video_path.exists():
        raise HTTPException(404, "Video not found")
    return FileResponse(str(video_path), media_type="video/x-msvideo")


@app.post("/api/jobs/{job_id}/mesh")
async def trigger_mesh(job_id: str):
    masks_dir = JOBS_DIR / job_id / "output" / "masks"
    if not masks_dir.exists():
        raise HTTPException(404, "Masks not found. Run inference first.")
    if not MESHLIB_AVAILABLE:
        raise HTTPException(500, "meshlib not installed on server")
    try:
        stl_path = await asyncio.to_thread(generate_mesh, str(masks_dir))
        return {"stl_path": str(stl_path), "status": "ok"}
    except Exception as e:
        raise HTTPException(500, f"Mesh generation failed: {e}") from e


@app.get("/api/jobs/{job_id}/mesh.stl")
async def get_mesh(job_id: str):
    stl_path = JOBS_DIR / job_id / "output" / "masks" / "mesh3D.stl"
    if not stl_path.exists():
        raise HTTPException(404, "Mesh not found. Trigger mesh generation first.")
    return FileResponse(
        str(stl_path),
        media_type="application/sla",
        filename="aorta_mesh.stl",
    )


@app.get("/api/jobs/{job_id}/diameter/{n}")
async def get_diameter(job_id: str, n: int, pixel_scale: float = Query(0.03378)):
    if not DIAMETER_AVAILABLE:
        raise HTTPException(500, "Diameter service unavailable: opencv not installed")
    mask_path = JOBS_DIR / job_id / "output" / "masks" / f"mask_{n:04d}.tiff"
    if not mask_path.exists():
        raise HTTPException(404, "Mask not found for this frame")
    result = measure_diameter(str(mask_path), pixel_scale)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@app.get("/api/jobs/{job_id}/diameter-improved/{n}")
async def get_diameter_improved(job_id: str, n: int, pixel_scale: float = Query(0.03378)):
    if not DIAMETER_AVAILABLE:
        raise HTTPException(500, "Diameter service unavailable: opencv not installed")
    mask_path = JOBS_DIR / job_id / "output" / "masks" / f"mask_{n:04d}.tiff"
    if not mask_path.exists():
        raise HTTPException(404, "Mask not found for this frame")
    result = measure_diameter_improved(str(mask_path), pixel_scale)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@app.post("/api/jobs/{job_id}/mesh-improved")
async def trigger_mesh_improved(job_id: str):
    masks_dir = JOBS_DIR / job_id / "output" / "masks"
    if not masks_dir.exists():
        raise HTTPException(404, "Masks not found. Run inference first.")
    if not IMPROVED_MESH_AVAILABLE:
        raise HTTPException(500, "Improved mesh dependencies not installed (scikit-image, trimesh)")
    try:
        stl_path = await asyncio.to_thread(generate_mesh_improved, str(masks_dir))
        return {"stl_path": str(stl_path), "status": "ok"}
    except Exception as e:
        raise HTTPException(500, f"Improved mesh generation failed: {e}") from e


@app.get("/api/jobs/{job_id}/mesh-improved.stl")
async def get_mesh_improved(job_id: str):
    stl_path = JOBS_DIR / job_id / "output" / "masks" / "mesh3D_improved.stl"
    if not stl_path.exists():
        raise HTTPException(404, "Improved mesh not found. Trigger generation first.")
    return FileResponse(
        str(stl_path),
        media_type="application/sla",
        filename="aorta_mesh_improved.stl",
    )


@app.get("/api/models")
async def list_models():
    models = []
    if MODELS_DIR.exists():
        for p in sorted(MODELS_DIR.glob("*.pt")):
            models.append({"name": p.name, "active": p.name == active_model_name})
    return models


@app.post("/api/models/switch")
async def switch_model(body: dict):
    global active_model_name
    name = body.get("name", "")
    if not name or not name.endswith(".pt"):
        raise HTTPException(400, "Invalid model name")
    model_path = MODELS_DIR / name
    if not model_path.exists():
        raise HTTPException(404, f"Model '{name}' not found")
    resolved = model_path.resolve()
    if not str(resolved).startswith(str(MODELS_DIR.resolve())):
        raise HTTPException(400, "Path traversal not allowed")

    running = [j for j in jobs.values() if j["state"] not in ("done", "error")]
    if running:
        raise HTTPException(409, "Cannot switch models while a job is running")

    if not INFERENCE_AVAILABLE:
        raise HTTPException(500, "Inference unavailable: torch/torchvision not installed")

    try:
        load_model(str(model_path))
        active_model_name = name
        thread = threading.Thread(target=warmup_model, daemon=True)
        thread.start()
        return {"status": "ok", "active_model": name}
    except Exception as e:
        raise HTTPException(500, f"Failed to load model: {e}") from e


@app.get("/api/status")
async def server_status():
    gpu = TORCH_AVAILABLE and torch.cuda.is_available()
    ms = "not_loaded"
    msd = ""
    if _inference_mod is not None:
        ms = _inference_mod.model_status
        msd = _inference_mod.model_status_detail
    return {
        "gpu_available": gpu,
        "gpu_name": torch.cuda.get_device_name(0) if gpu else None,
        "device": str(torch.device("cuda" if gpu else "cpu")) if TORCH_AVAILABLE else "unavailable",
        "meshlib_available": MESHLIB_AVAILABLE,
        "inference_available": INFERENCE_AVAILABLE,
        "model_status": ms,
        "model_status_detail": msd,
        "active_model": active_model_name,
        "active_jobs": len([j for j in jobs.values() if j["state"] not in ("done", "error")]),
    }


if FRONTEND_DIR.exists():
    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
