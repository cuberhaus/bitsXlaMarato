"""Improved 3D mesh generation: Gaussian smoothing + marching cubes + Taubin filtering."""

from __future__ import annotations

import os
from glob import glob
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    from scipy.ndimage import gaussian_filter
    from skimage.measure import marching_cubes
    import trimesh
    import trimesh.smoothing

    IMPROVED_MESH_AVAILABLE = True
except ImportError:
    IMPROVED_MESH_AVAILABLE = False


def _load_mask_volume(masks_dir: str) -> np.ndarray:
    """Load all mask TIFFs into a 3D numpy array (z, y, x), binarized to 0.0/1.0."""
    paths = sorted(glob(os.path.join(masks_dir, "mask_*.tiff")))
    if not paths:
        raise RuntimeError(f"No mask_*.tiff files found in {masks_dir}")

    slices = []
    for p in paths:
        img = Image.open(p)
        data = np.array(img)
        if data.ndim == 3:
            data = data[:, :, 0]
        binary = (data > 128).astype(np.float32)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        # Slight dilation to ensure thin regions stay connected between frames
        binary = cv2.dilate(binary, kernel, iterations=1)
        slices.append(binary)

    return np.stack(slices, axis=0)


def generate_mesh_improved(
    masks_dir: str,
    smooth_iterations: int = 30,
) -> Path:
    """Generate a smooth STL mesh from mask TIFFs using marching cubes + Taubin smoothing.

    Uses anisotropic Gaussian blur (heavier in z to bridge inter-frame gaps)
    and a low marching cubes threshold to keep thin regions connected.
    """
    if not IMPROVED_MESH_AVAILABLE:
        raise RuntimeError(
            "Required packages not installed. Run: pip install scikit-image trimesh scipy"
        )

    volume = _load_mask_volume(masks_dir)

    # Anisotropic blur: heavier in z (between frames) to bridge gaps,
    # lighter in xy to preserve in-plane detail
    smoothed = gaussian_filter(volume, sigma=(4.0, 2.0, 2.0))

    # Low threshold keeps thin/bridged regions connected
    verts, faces, normals, _ = marching_cubes(
        smoothed, level=0.3, spacing=(1.5, 1.0, 1.0)
    )

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)

    # Keep only the largest connected component to discard small fragments
    components = mesh.split(only_watertight=False)
    if components:
        mesh = max(components, key=lambda m: m.volume if m.is_volume else len(m.faces))

    trimesh.smoothing.filter_taubin(mesh, iterations=smooth_iterations)

    stl_path = os.path.join(masks_dir, "mesh3D_improved.stl")
    if os.path.exists(stl_path):
        os.remove(stl_path)
    mesh.export(stl_path)

    return Path(stl_path)
