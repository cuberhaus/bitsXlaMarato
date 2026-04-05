import { Component, Input, OnInit, OnDestroy, EventEmitter, Output, NgZone } from '@angular/core';
import { ApiService, JobStatus } from '../../services/api';

@Component({
  selector: 'app-job-status',
  standalone: true,
  templateUrl: './job-status.html',
  styleUrl: './job-status.css',
})
export class JobStatusComponent implements OnInit, OnDestroy {
  @Input() jobId = '';
  @Output() completed = new EventEmitter<void>();
  @Output() failed = new EventEmitter<string>();

  status: JobStatus = { state: 'uploading', progress: 0, total: 0, message: 'Starting...' };
  private eventSource: EventSource | null = null;

  constructor(private api: ApiService, private zone: NgZone) {}

  ngOnInit() {
    if (!this.jobId) return;
    this.eventSource = this.api.createSSE(this.jobId);
    this.eventSource.onmessage = (event) => {
      this.zone.run(() => {
        this.status = JSON.parse(event.data);
        if (this.status.state === 'done' || this.status.state === 'error') {
          this.eventSource?.close();
          if (this.status.state === 'done') {
            this.completed.emit();
          } else {
            this.failed.emit(this.status.message);
          }
        }
      });
    };
    this.eventSource.onerror = () => {
      this.zone.run(() => {
        this.eventSource?.close();
        this.status = { ...this.status, state: 'error', message: 'Connection to server lost.' };
        this.failed.emit(this.status.message);
      });
    };
  }

  ngOnDestroy() {
    this.eventSource?.close();
  }

  get progressPercent(): number {
    if (this.status.total === 0) return 0;
    return Math.round((this.status.progress / this.status.total) * 100);
  }

  get stateLabel(): string {
    const labels: Record<string, string> = {
      uploading: 'Uploading',
      extracting: 'Extracting Frames',
      inferring: 'Running Inference',
      composing: 'Composing Video',
      done: 'Complete',
      error: 'Error',
    };
    return labels[this.status.state] || this.status.state;
  }
}
