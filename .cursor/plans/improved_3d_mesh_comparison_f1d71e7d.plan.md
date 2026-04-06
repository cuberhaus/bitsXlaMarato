---
name: Improved 3D mesh and measurement comparison
overview: Add improved 3D mesh generation (marching cubes + smoothing) and improved diameter measurement (Feret diameter + ellipse fit) alongside the original hackathon implementations, displayed side-by-side in the UI.
todos:
  - id: mesh-improved-backend
    content: Create web/backend/services/mesh_improved.py with the improved pipeline (Gaussian blur + marching cubes + Taubin smoothing)
    status: completed
  - id: diameter-improved-backend
    content: Add measure_diameter_improved() to diameter.py using Feret diameter + ellipse fit
    status: completed
  - id: deps
    content: Add scikit-image and trimesh to requirements.txt
    status: completed
  - id: api-endpoints
    content: Add mesh-improved and diameter-improved endpoints in app.py
    status: completed
  - id: api-service
    content: Add improved mesh and diameter methods to frontend api.ts
    status: completed
  - id: three-viewer-method
    content: Add method input to three-viewer component to support original vs improved
    status: completed
  - id: diameter-method
    content: Add method input to diameter component to support original vs improved
    status: completed
  - id: side-by-side-layout
    content: Update app.html and app.css to show original vs improved for both 3D and measurement
    status: completed
isProject: false
---

# Improved 3D Mesh and Measurement: Side-by-Side Comparison

---

## Part 1: 3D Mesh

### Current Mesh Pipeline (meshlib) -- What's Wrong

The current `[web/backend/services/mesh.py](web/backend/services/mesh.py)`:

- **No pre-processing**: Raw binary masks go straight into meshing, producing jagged, blocky surfaces
- **Uniform voxel size `(1,1,1)`**: Ignores that inter-frame spacing (z) is likely different from pixel spacing (xy), causing distorted proportions
- **No post-processing**: No mesh smoothing or decimation
- `**isoValue=127`** on already-binary (0/255) data means the isosurface is just the staircase boundary between voxels

### Improved Mesh Pipeline

New file `web/backend/services/mesh_improved.py` using **scikit-image** + **trimesh**:

```
Binary masks (TIFF stack)
  -> Load into 3D numpy volume (z, y, x)
  -> Morphological closing per-slice (fill small holes in masks)
  -> 3D Gaussian blur (sigma ~2) to create a smooth scalar field
  -> Marching cubes (scikit-image, level=0.5, spacing=(z_scale, 1, 1))
  -> Taubin smoothing via trimesh (preserves volume, unlike basic Laplacian)
  -> Export as STL
```

Key improvements:

- **Gaussian blur** turns the blocky binary volume into a smooth field, so marching cubes produces organic surfaces
- **Taubin smoothing** reduces mesh noise without shrinking volume (unlike plain Laplacian)
- **Proper z-spacing** accounts for inter-frame distance != pixel size
- **Morphological closing** fixes small segmentation gaps per frame

---

## Part 2: Diameter Measurement

### Current Measurement -- What's Wrong

The current `[web/backend/services/diameter.py](web/backend/services/diameter.py)` `measure_diameter()`:

1. Finds all contours, picks the one with the **tallest bounding rect** (`max h`)
2. Returns bounding rect height `h` as "diameter"
3. Draws a measurement line at `y = top of bounding rect` spanning the full image width

Problems:

- **Bounding rect height is not diameter** -- it's the vertical extent, which overestimates for tilted shapes and ignores the actual widest cross-section
- **Picks contour by tallest bounding rect**, not by area -- may pick a thin tall artifact over the actual aorta
- **Measurement line is meaningless** -- drawn at the top edge, full image width, not at the actual widest point
- **No rotation invariance** -- a 45-degree-tilted circle gives a bounding rect ~41% larger than its true diameter

### Improved Measurement

Add `measure_diameter_improved()` to the existing `[diameter.py](web/backend/services/diameter.py)`:

1. Find the **largest contour by area** (most likely the aorta, filters out small noise)
2. Compute the **maximum Feret diameter** -- the maximum distance between any two points on the convex hull. This is the clinically standard measurement for AAA assessment. Computed via rotating calipers on the convex hull in O(n) time
3. Fit a **minimum enclosing ellipse** via `cv2.fitEllipse()` -- provides major/minor axis lengths as supplementary data
4. Return the actual **two endpoints** of the maximum Feret diameter for accurate line overlay
5. Also return the ellipse parameters (center, axes, angle) for optional visualization

```python
def measure_diameter_improved(mask_path: str, pixel_scale: float = 0.03378) -> dict:
    # ... load and threshold same as original ...
    # Pick largest contour by area
    contour = max(contours, key=cv2.contourArea)
    # Convex hull -> max Feret diameter (rotating calipers)
    hull = cv2.convexHull(contour).squeeze()
    # Find pair of hull points with maximum distance
    max_dist, pt1, pt2 = feret_diameter(hull)
    # Ellipse fit for supplementary info
    ellipse = cv2.fitEllipse(contour)
    return {
        "diameter_px": max_dist,
        "diameter_cm": round(max_dist * pixel_scale, 4),
        "measurement_line": {"x1": pt1[0], "y1": pt1[1], "x2": pt2[0], "y2": pt2[1]},
        "ellipse": {"cx": ..., "cy": ..., "major": ..., "minor": ..., "angle": ...},
        "pixel_scale": pixel_scale,
        "method": "feret",
    }
```

The improved measurement returns a different `measurement_line` shape (x1/y1/x2/y2 endpoints instead of y/x_start/x_end) since the Feret diameter can be at any angle.

---

## Changes

### 1. New backend service: `web/backend/services/mesh_improved.py`

- `generate_mesh_improved(masks_dir, z_spacing=3.0, sigma=2.0, smooth_iterations=15) -> Path`
- Loads masks, morphological closing, Gaussian blur, marching cubes, Taubin smoothing
- Exports to `mesh3D_improved.stl`

### 2. Improved measurement in `[web/backend/services/diameter.py](web/backend/services/diameter.py)`

- Add `measure_diameter_improved()` alongside the existing `measure_diameter()`
- Feret diameter via convex hull max distance
- Ellipse fit for additional context
- Returns endpoint-based measurement line for accurate overlay

### 3. New dependencies in `[web/backend/requirements.txt](web/backend/requirements.txt)`

- `scikit-image` (for marching cubes)
- `trimesh` (for Taubin smoothing + STL export)
- `scipy` is already a transitive dep of scikit-image

### 4. New API endpoints in `[web/backend/app.py](web/backend/app.py)`

- `POST /api/jobs/{job_id}/mesh-improved` -- triggers improved mesh generation
- `GET /api/jobs/{job_id}/mesh-improved.stl` -- serves the improved STL
- `GET /api/jobs/{job_id}/diameter-improved/{n}?pixel_scale=...` -- improved diameter measurement

### 5. Frontend API service: `[web/frontend/src/app/services/api.ts](web/frontend/src/app/services/api.ts)`

- Add `triggerMeshImproved(jobId)`, `getMeshImprovedUrl(jobId)`
- Add `getDiameterImproved(jobId, frameIndex, pixelScale)`
- Add `DiameterImprovedResult` interface (different `measurement_line` shape + ellipse data)

### 6. Three viewer: `[web/frontend/src/app/components/three-viewer/](web/frontend/src/app/components/three-viewer/)`

- Add `@Input() method: 'original' | 'improved' = 'original'`
- Route generate/load to correct API based on `method`

### 7. Diameter component: `[web/frontend/src/app/components/diameter/](web/frontend/src/app/components/diameter/)`

- Add `@Input() method: 'original' | 'improved' = 'original'`
- Call the appropriate API
- Render the measurement line differently: original uses horizontal line, improved uses angled line between endpoints
- Show ellipse overlay when method is improved (dashed ellipse drawn via SVG)

### 8. Dashboard layout: `[app.html](web/frontend/src/app/app.html)` + `[app.css](web/frontend/src/app/app.css)`

Replace the current single-column measurement card and single 3D card with a comparison layout:

```
+---------------------------------------------------------------+
| FRAME VIEWER                                                   |
+-------------------------------+-------------------------------+
| MEASUREMENT -- ORIGINAL       | MEASUREMENT -- IMPROVED       |
| (bounding rect height)        | (Feret diameter + ellipse)    |
|  2.0606 cm                    |  1.87 cm                      |
|  [mask + horiz line]          |  [mask + angled line + ellipse]|
+-------------------------------+-------------------------------+
| 3D MODEL -- ORIGINAL          | 3D MODEL -- IMPROVED          |
| [Generate]                    | [Generate]                    |
| [blocky canvas]               | [smooth canvas]               |
+-------------------------------+-------------------------------+
```

- Frame viewer stays full width (top row, unchanged)
- Measurement: two cards side by side in a `.measurements-grid` (1fr 1fr)
- 3D models: two cards side by side in a `.models-grid` (1fr 1fr)
- Both grids stack vertically on screens below 900px

