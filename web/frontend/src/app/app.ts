import { Component } from '@angular/core';
import { UploadComponent } from './components/upload/upload';
import { JobStatusComponent } from './components/job-status/job-status';
import { FrameViewerComponent } from './components/frame-viewer/frame-viewer';
import { ThreeViewerComponent } from './components/three-viewer/three-viewer';
import { DiameterComponent } from './components/diameter/diameter';
import { ApiService, ServerStatus } from './services/api';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    UploadComponent,
    JobStatusComponent,
    FrameViewerComponent,
    ThreeViewerComponent,
    DiameterComponent,
  ],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class AppComponent {
  jobId = '';
  activeTab: 'frames' | '3d' | 'measurement' = 'frames';
  processing = false;
  selectedFrame = 0;
  serverStatus: ServerStatus | null = null;

  constructor(private api: ApiService) {
    this.api.getServerStatus().subscribe({
      next: (s) => (this.serverStatus = s),
    });
  }

  onJobStarted(jobId: string) {
    this.jobId = jobId;
    this.processing = true;
    this.activeTab = 'frames';
  }

  onJobCompleted() {
    this.processing = false;
  }

  onFrameSelected(index: number) {
    this.selectedFrame = index;
  }

  resetJob() {
    this.jobId = '';
    this.processing = false;
    this.selectedFrame = 0;
  }
}
