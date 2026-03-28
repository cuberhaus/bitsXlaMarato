"""3D mesh generation service: TIFF mask stack -> STL mesh via meshlib."""

from __future__ import annotations

import os
from glob import glob
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    import meshlib.mrmeshpy as mr

    MESHLIB_AVAILABLE = True
except ImportError:
    MESHLIB_AVAILABLE = False


def binarize_masks(masks_dir: str) -> None:
    """Convert RGB mask TIFFs to binary grayscale for meshlib."""
    for tiff_path in sorted(glob(os.path.join(masks_dir, "*.tiff"))):
        img = Image.open(tiff_path)
        data = np.array(img)
        if data.ndim == 3:
            binary = data[:, :, 0]
        else:
            binary = data
        cv2.imwrite(tiff_path, binary)


def generate_mesh(masks_dir: str) -> Path:
    """Generate STL mesh from mask TIFFs. Returns path to the STL file."""
    if not MESHLIB_AVAILABLE:
        raise RuntimeError(
            "meshlib is not installed. Install with: pip install meshlib"
        )

    binarize_masks(masks_dir)

    stl_path = os.path.join(masks_dir, "mesh3D.stl")
    if os.path.exists(stl_path):
        os.remove(stl_path)

    settings = mr.LoadingTiffSettings()
    settings.dir = masks_dir
    settings.voxelSize = mr.Vector3f(1, 1, 1)

    volume = mr.loadTiffDir(settings)
    mesh = mr.gridToMesh(volume.value(), 127.0)
    mr.saveMesh(mesh.value(), mr.Path(stl_path))

    return Path(stl_path)
