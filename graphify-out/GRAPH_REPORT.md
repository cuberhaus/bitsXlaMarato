# Graph Report - .  (2026-06-19)

## Corpus Check
- 71 files · ~25,975 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 56 nodes · 58 edges · 12 communities (8 shown, 4 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_3D Mesh Generation|3D Mesh Generation]]
- [[_COMMUNITY_Diameter Measurement|Diameter Measurement]]
- [[_COMMUNITY_Model Loading & Mask R-CNN|Model Loading & Mask R-CNN]]
- [[_COMMUNITY_AAA Clinical Pipeline|AAA Clinical Pipeline]]
- [[_COMMUNITY_GPU Inference Pipeline|GPU Inference Pipeline]]
- [[_COMMUNITY_Video Upload & API|Video Upload & API]]
- [[_COMMUNITY_Job Orchestration & Frames|Job Orchestration & Frames]]
- [[_COMMUNITY_App Shell & Server Status|App Shell & Server Status]]
- [[_COMMUNITY_Mask Serving (PNG cache)|Mask Serving (PNG cache)]]
- [[_COMMUNITY_Frame Viewer|Frame Viewer]]
- [[_COMMUNITY_ImageSize Type|ImageSize Type]]
- [[_COMMUNITY_MeasurementLine Type|MeasurementLine Type]]

## God Nodes (most connected - your core abstractions)
1. `run_inference()` - 8 edges
2. `_run_job()` - 5 edges
3. `Aorta Segmentation` - 4 edges
4. `Mask R-CNN Model` - 4 edges
5. `GPU Inference Pipeline` - 4 edges
6. `load_model()` - 4 edges
7. `measure_diameter()` - 4 edges
8. `upload_video endpoint` - 4 edges
9. `DiameterComponent` - 3 edges
10. `ApiService` - 3 edges

## Surprising Connections (you probably didn't know these)
- `DiameterComponent` --references--> `Aorta Diameter Measurement`  [INFERRED]
  web/frontend/src/app/components/diameter/diameter.ts → README.md
- `ThreeViewerComponent` --references--> `3D Mesh Reconstruction`  [INFERRED]
  web/frontend/src/app/components/three-viewer/three-viewer.ts → README.md
- `extract_frames()` --implements--> `Ultrasound Frame Extraction`  [EXTRACTED]
  web/backend/services/inference.py → README.md
- `run_inference()` --implements--> `Aorta Segmentation`  [EXTRACTED]
  web/backend/services/inference.py → README.md
- `run_inference()` --implements--> `Pipelined Batched Inference`  [EXTRACTED]
  web/backend/services/inference.py → PERFORMANCE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Video Inference Job Pipeline** — backend_app_run_job, services_inference_extract_frames, services_inference_run_inference, services_inference_compose_video [EXTRACTED 1.00]
- **Diameter Measurement Methods (original vs improved)** — services_diameter_measure_diameter, services_diameter_measure_diameter_improved, concept_diameter_measurement [EXTRACTED 0.90]
- **3D Mesh Reconstruction Methods (meshlib vs marching cubes)** — services_mesh_generate_mesh, services_mesh_improved_generate_mesh_improved, concept_3d_reconstruction [EXTRACTED 0.90]

## Communities (12 total, 4 thin omitted)

### Community 0 - "3D Mesh Generation"
Cohesion: 0.25
Nodes (8): trigger_mesh endpoint, trigger_mesh_improved endpoint, Marching Cubes Mesh (improved), meshlib STL Mesh (original), asyncio.to_thread Offloading, Taubin Mesh Smoothing, generate_mesh(), generate_mesh_improved()

### Community 1 - "Diameter Measurement"
Cohesion: 0.29
Nodes (8): Bounding-Rect Diameter (original), Ellipse-Fit Diameter (improved), DiameterComponent, DiameterImprovedResult, DiameterResult, measure_diameter(), measure_diameter_improved(), distanceFinder.py (hackathon diameter)

### Community 2 - "Model Loading & Mask R-CNN"
Cohesion: 0.33
Nodes (7): FastAPI app (app:app), Mask R-CNN Model, Mask R-CNN Fine-Tuning (training), cuDNN Warmup Pass, Avoid torch.compile (Mask R-CNN incompatible), load_model(), warmup_model()

### Community 3 - "AAA Clinical Pipeline"
Cohesion: 0.29
Nodes (7): 3D Mesh Reconstruction, Abdominal Aortic Aneurysm (AAA), Aneurysm Detection, Aorta Segmentation, Aorta Diameter Measurement, Ultrasound Frame Extraction, ThreeViewerComponent

### Community 4 - "GPU Inference Pipeline"
Cohesion: 0.33
Nodes (6): GPU Inference Pipeline, FastAPI + Angular Web App, AMP float16 Inference, Pinned Memory + non_blocking DMA, Pipelined Batched Inference, run_inference()

### Community 5 - "Video Upload & API"
Cohesion: 0.40
Nodes (5): get_diameter endpoint, upload_video endpoint, Streaming Chunked Upload, ApiService, UploadComponent

### Community 6 - "Job Orchestration & Frames"
Cohesion: 0.40
Nodes (4): _run_job(), JobStatusComponent, JobStatus, extract_frames()

### Community 7 - "App Shell & Server Status"
Cohesion: 0.67
Nodes (3): AppComponent, ModelInfo, ServerStatus

## Knowledge Gaps
- **12 isolated node(s):** `FrameViewerComponent`, `JobStatusComponent`, `ThreeViewerComponent`, `UploadComponent`, `MeasurementLine` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_inference()` connect `GPU Inference Pipeline` to `Model Loading & Mask R-CNN`, `AAA Clinical Pipeline`, `Job Orchestration & Frames`?**
  _High betweenness centrality (0.340) - this node is a cross-community bridge._
- **Why does `_run_job()` connect `Job Orchestration & Frames` to `GPU Inference Pipeline`, `Video Upload & API`?**
  _High betweenness centrality (0.314) - this node is a cross-community bridge._
- **Why does `ApiService` connect `Video Upload & API` to `3D Mesh Generation`?**
  _High betweenness centrality (0.309) - this node is a cross-community bridge._
- **What connects `FrameViewerComponent`, `JobStatusComponent`, `ThreeViewerComponent` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._