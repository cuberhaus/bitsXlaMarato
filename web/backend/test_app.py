"""Tests for the bitsXlaMarato FastAPI backend.

These tests exercise endpoints that work without GPU/model dependencies.
"""

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_status():
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "gpu_available" in data
    assert "inference_available" in data
    assert "model_status" in data
    assert "active_model" in data


def test_models_list():
    r = client.get("/api/models")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_job_not_found_status():
    r = client.get("/api/jobs/nonexistent-id/status-poll")
    assert r.status_code == 404


def test_job_not_found_frames():
    r = client.get("/api/jobs/nonexistent-id/frames")
    assert r.status_code == 404


def test_job_not_found_overlays():
    r = client.get("/api/jobs/nonexistent-id/overlays")
    assert r.status_code == 404


def test_job_not_found_video():
    r = client.get("/api/jobs/nonexistent-id/video")
    assert r.status_code == 404


def test_job_not_found_mesh():
    r = client.post("/api/jobs/nonexistent-id/mesh")
    assert r.status_code == 404


def test_switch_model_nonexistent():
    r = client.post("/api/models/switch", json={"name": "nonexistent.pt"})
    assert r.status_code in (400, 404)
