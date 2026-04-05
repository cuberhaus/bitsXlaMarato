import { Component, Input, OnInit, OnDestroy, EventEmitter, Output, ChangeDetectorRef } from '@angular/core';
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
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private done = false;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    if (!this.jobId) return;
    this.poll();
    this.pollTimer = setInterval(() => this.poll(), 500);
  }

  ngOnDestroy() {
    this.stopPolling();
  }

  private stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  private poll() {
    if (this.done) return;
    this.api.pollJobStatus(this.jobId).subscribe({
      next: (s) => {
        this.status = s;
        this.cdr.detectChanges();
        if (s.state === 'done') {
          this.done = true;
          this.stopPolling();
          this.completed.emit();
        } else if (s.state === 'error') {
          this.done = true;
          this.stopPolling();
          this.failed.emit(s.message);
        }
      },
      error: () => {
        this.done = true;
        this.stopPolling();
        this.status = { ...this.status, state: 'error', message: 'Lost connection to server.' };
        this.failed.emit(this.status.message);
        this.cdr.detectChanges();
      },
    });
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
