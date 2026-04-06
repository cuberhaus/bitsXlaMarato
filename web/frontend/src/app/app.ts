import { Component, OnDestroy } from '@angular/core';
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
export class AppComponent implements OnDestroy {
  jobId = '';
  processing = false;
  selectedFrame = 0;
  errorMessage = '';
  serverStatus: ServerStatus | null = null;
  compileElapsed = 0;
  private statusPoll: ReturnType<typeof setInterval> | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService) {
    this.fetchStatus();
    this.statusPoll = setInterval(() => this.fetchStatus(), 2000);
    this.timer = setInterval(() => {
      if (this.serverStatus && this.serverStatus.model_status !== 'ready') {
        this.compileElapsed++;
      }
    }, 1000);
  }

  ngOnDestroy() {
    if (this.statusPoll) clearInterval(this.statusPoll);
    if (this.timer) clearInterval(this.timer);
  }

  private fetchStatus() {
    this.api.getServerStatus().subscribe({
      next: (s) => {
        this.serverStatus = s;
        if (s.model_status === 'ready') {
          if (this.statusPoll) { clearInterval(this.statusPoll); this.statusPoll = null; }
          if (this.timer) { clearInterval(this.timer); this.timer = null; }
        }
      },
    });
  }

  onJobStarted(jobId: string) {
    this.jobId = jobId;
    this.processing = true;
    this.errorMessage = '';
  }

  onJobCompleted() {
    this.processing = false;
  }

  onJobFailed(message: string) {
    this.processing = false;
    this.errorMessage = message;
  }

  onFrameSelected(index: number) {
    this.selectedFrame = index;
  }

  resetJob() {
    this.jobId = '';
    this.processing = false;
    this.errorMessage = '';
    this.selectedFrame = 0;
  }
}
