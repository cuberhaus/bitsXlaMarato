import { Component, OnDestroy, ChangeDetectorRef, NgZone } from '@angular/core';
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
  private poll: ReturnType<typeof setInterval> | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef, private zone: NgZone) {
    this.zone.runOutsideAngular(() => {
      this.timer = setInterval(() => {
        if (this.serverStatus && this.serverStatus.model_status !== 'ready') {
          this.compileElapsed++;
          this.zone.run(() => this.cdr.detectChanges());
        }
      }, 1000);
      this.poll = setInterval(() => this.fetchStatus(), 2000);
    });
    this.fetchStatus();
  }

  ngOnDestroy() {
    if (this.poll) clearInterval(this.poll);
    if (this.timer) clearInterval(this.timer);
  }

  private fetchStatus() {
    this.api.getServerStatus().subscribe({
      next: (s) => {
        this.zone.run(() => {
          this.serverStatus = s;
          this.cdr.detectChanges();
          if (s.model_status === 'ready') {
            if (this.poll) { clearInterval(this.poll); this.poll = null; }
            if (this.timer) { clearInterval(this.timer); this.timer = null; }
          }
        });
      },
      error: () => {},
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
