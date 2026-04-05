import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface JobStatus {
  state: string;
  progress: number;
  total: number;
  message: string;
}

export interface MeasurementLine {
  x1: number; y1: number; x2: number; y2: number;
}

export interface ImageSize {
  w: number; h: number;
}

export interface DiameterResult {
  diameter_px: number;
  diameter_cm: number;
  bounding_rect: { x: number; y: number; w: number; h: number };
  measurement_line: MeasurementLine;
  image_size: ImageSize;
  pixel_scale: number;
}

export interface DiameterImprovedResult {
  diameter_px: number;
  diameter_cm: number;
  bounding_rect: { x: number; y: number; w: number; h: number };
  measurement_line: MeasurementLine;
  ellipse: { cx: number; cy: number; major: number; minor: number; angle: number } | null;
  image_size: ImageSize;
  pixel_scale: number;
  method: string;
}

export interface ServerStatus {
  gpu_available: boolean;
  gpu_name: string | null;
  device: string;
  meshlib_available: boolean;
  active_jobs: number;
}

const API = '/api';

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  uploadVideo(file: File, confidence: number, useCrop: boolean): Observable<{ job_id: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const params = new HttpParams()
      .set('confidence', confidence.toString())
      .set('use_crop', useCrop.toString());
    return this.http.post<{ job_id: string }>(`${API}/upload`, formData, { params });
  }

  pollJobStatus(jobId: string): Observable<JobStatus> {
    return this.http.get<JobStatus>(`${API}/jobs/${jobId}/status-poll`);
  }

  createSSE(jobId: string): EventSource {
    return new EventSource(`${API}/jobs/${jobId}/status`);
  }

  listFrames(jobId: string): Observable<{ frames: string[]; count: number }> {
    return this.http.get<{ frames: string[]; count: number }>(`${API}/jobs/${jobId}/frames`);
  }

  getFrameUrl(jobId: string, n: number): string {
    return `${API}/jobs/${jobId}/frames/${n}`;
  }

  listOverlays(jobId: string): Observable<{ overlays: string[]; count: number }> {
    return this.http.get<{ overlays: string[]; count: number }>(`${API}/jobs/${jobId}/overlays`);
  }

  getOverlayUrl(jobId: string, n: number): string {
    return `${API}/jobs/${jobId}/overlays/${n}`;
  }

  getMaskUrl(jobId: string, n: number): string {
    return `${API}/jobs/${jobId}/masks/${n}`;
  }

  getVideoUrl(jobId: string): string {
    return `${API}/jobs/${jobId}/video`;
  }

  triggerMesh(jobId: string): Observable<{ stl_path: string; status: string }> {
    return this.http.post<{ stl_path: string; status: string }>(`${API}/jobs/${jobId}/mesh`, {});
  }

  getMeshUrl(jobId: string): string {
    return `${API}/jobs/${jobId}/mesh.stl`;
  }

  triggerMeshImproved(jobId: string): Observable<{ stl_path: string; status: string }> {
    return this.http.post<{ stl_path: string; status: string }>(`${API}/jobs/${jobId}/mesh-improved`, {});
  }

  getMeshImprovedUrl(jobId: string): string {
    return `${API}/jobs/${jobId}/mesh-improved.stl`;
  }

  getDiameter(jobId: string, frameIndex: number, pixelScale = 0.03378): Observable<DiameterResult> {
    const params = new HttpParams().set('pixel_scale', pixelScale.toString());
    return this.http.get<DiameterResult>(`${API}/jobs/${jobId}/diameter/${frameIndex}`, { params });
  }

  getDiameterImproved(jobId: string, frameIndex: number, pixelScale = 0.03378): Observable<DiameterImprovedResult> {
    const params = new HttpParams().set('pixel_scale', pixelScale.toString());
    return this.http.get<DiameterImprovedResult>(`${API}/jobs/${jobId}/diameter-improved/${frameIndex}`, { params });
  }

  getServerStatus(): Observable<ServerStatus> {
    return this.http.get<ServerStatus>(`${API}/status`);
  }
}
