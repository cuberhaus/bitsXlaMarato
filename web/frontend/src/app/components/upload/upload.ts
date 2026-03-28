import { Component, EventEmitter, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './upload.html',
  styleUrl: './upload.css',
})
export class UploadComponent {
  @Output() jobStarted = new EventEmitter<string>();

  confidence = 0.9;
  useCrop = true;
  dragging = false;
  uploading = false;
  selectedFile: File | null = null;

  constructor(private api: ApiService) {}

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.dragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.dragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragging = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.selectedFile = files[0];
      this.upload();
    }
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
    }
  }

  upload() {
    if (!this.selectedFile) return;
    this.uploading = true;
    this.api.uploadVideo(this.selectedFile, this.confidence, this.useCrop).subscribe({
      next: (res) => {
        this.uploading = false;
        this.jobStarted.emit(res.job_id);
      },
      error: (err) => {
        this.uploading = false;
        alert('Upload failed: ' + (err.error?.detail || err.message));
      },
    });
  }
}
