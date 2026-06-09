# bitsXlaMarato

Award-winning project from the 2022 BitsxlaMarató (TV3) hackathon "per la salut cardiovascular": abdominal aortic aneurysm detection from ultrasound video using a fine-tuned Mask R-CNN, with 3D mesh reconstruction. The original hackathon scripts/notebooks live alongside a modernized FastAPI + Angular web app added later.

## Architecture

- [web/](web/) — Current entry point. `backend/` is a FastAPI app (`app:app`, port `8001`) that runs inference and mesh generation; `frontend/` is an Angular app (port `4200`). The backend's own deps live in [web/backend/requirements.txt](web/backend/requirements.txt) (not the root one).
- [models/](models/) — Trained Mask R-CNN weights (`marato.pt`, `maratoNuevo.pt`). Stored via **Git LFS** — `git lfs pull` is required on first clone.
- [MASKRCNN/](MASKRCNN/) — Original training code: `engine.py`, `coco_utils.py`, `transforms.py`, `mask.py`, `inference.py` (torchvision detection reference style).
- [src/](src/) — Hackathon-era utility scripts and notebooks: frame extraction (`Convert video in frames.ipynb`, `video_to_frame.ipynb`), `distanceFinder.py`, `ImageViewer.py`.
- [3D approximation/](3D%20approximation/) — Notebooks (`este va! aorta 3d y bin tiff.ipynb`, `Reconocer aorta y generar 3d.ipynb`) that turn segmentation masks into an STL mesh. Production version lives under `web/backend/services/`.
- [annotations/](annotations/) — Hand-made COCO and VGG JSON annotations for patients 541/588/601/603.
- [frames/](frames/) — Extracted per-patient frame folders used for training/eval (large, gitignored content likely).
- [docs/](docs/) — Original challenge brief (`Challenge_1_V2.pdf/.pptx`).

## Build and Test

Use the [Makefile](Makefile), not the root `requirements.txt` (which is stale and has conflicting `opencv-python` versions).

- `make dev` — install deps + run backend on `:8001` and Angular on `:4200`.
- `make dev-backend` / `make dev-frontend` — run one side only.
- `make build` / `make serve` — production frontend build, served by FastAPI.
- `make docker-build` / `make docker-up` — build and run the [Dockerfile](Dockerfile) image (CUDA 12.4 runtime, GPU passthrough via [docker-compose.yml](docker-compose.yml)).
- `make clean-jobs` wipes `web/backend/jobs/`; `make clean` also removes `node_modules`, `dist`, `.venv`.

No automated test suite exists.

## Conventions

- Backend uses `torch.inference_mode()` + AMP `float16` + batch-16 pipelined I/O on GPU; do not regress this (see [PERFORMANCE.md](PERFORMANCE.md)).
- Long jobs (mesh generation, inference) must be offloaded via `asyncio.to_thread()` to keep the FastAPI event loop responsive.
- `Mask R-CNN is incompatible with torch.compile` — do not add it.

## Agent skills

Installable skills live under `web/.agents/skills/` (gitignored; restore with `make -C web skills-restore`). Pinned versions are in [web/skills-lock.json](web/skills-lock.json). Skills apply only to `web/` work — the hackathon-era code in `src/`, `MASKRCNN/`, and `3D approximation/` is frozen.

- **angular-component** — consult when creating or editing Angular components in `web/frontend/`.
- **threejs-fundamentals** — consult when working on Three.js 3D rendering / mesh visualization in the frontend.
- **fastapi-templates** — consult when adding or modifying endpoints in `web/backend/`.

## Pitfalls

- Hackathon-era code in `src/`, `MASKRCNN/`, and `3D approximation/` is largely archived; new work goes in `web/backend/`.
- Root [requirements.txt](requirements.txt) is **not** what the app uses — it pins `torchvision==0.14.1` against `torch==2.8.0` (incompatible) and lists `opencv-python` twice. Treat it as legacy.
- A CUDA-capable GPU is expected for real inference; CPU fallback will be very slow.
- `frames/`, `videos/`, and `models/` can be large; avoid bulk-reading them with tools.
- Folder name `3D approximation/` contains a space — quote it in shell commands.

See [README.md](README.md) and [PERFORMANCE.md](PERFORMANCE.md) for full context.
