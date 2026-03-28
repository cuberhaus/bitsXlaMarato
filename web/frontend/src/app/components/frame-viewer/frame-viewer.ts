import { Component, Input, OnInit, OnChanges, EventEmitter, Output, HostListener } from '@angular/core';
import { ApiService } from '../../services/api';

@Component({
  selector: 'app-frame-viewer',
  standalone: true,
  templateUrl: './frame-viewer.html',
  styleUrl: './frame-viewer.css',
})
export class FrameViewerComponent implements OnInit, OnChanges {
  @Input() jobId = '';
  @Output() frameSelected = new EventEmitter<number>();

  currentFrame = 0;
  totalFrames = 0;
  showOverlay = true;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.loadFrameCount();
  }

  ngOnChanges() {
    this.loadFrameCount();
  }

  private loadFrameCount() {
    if (!this.jobId) return;
    this.api.listFrames(this.jobId).subscribe({
      next: (res) => {
        this.totalFrames = res.count;
        this.currentFrame = 0;
      },
    });
  }

  get frameUrl(): string {
    if (!this.jobId) return '';
    return this.showOverlay
      ? this.api.getOverlayUrl(this.jobId, this.currentFrame)
      : this.api.getFrameUrl(this.jobId, this.currentFrame);
  }

  prevFrame() {
    if (this.currentFrame > 0) {
      this.currentFrame--;
      this.frameSelected.emit(this.currentFrame);
    }
  }

  nextFrame() {
    if (this.currentFrame < this.totalFrames - 1) {
      this.currentFrame++;
      this.frameSelected.emit(this.currentFrame);
    }
  }

  onSliderChange(event: Event) {
    const val = +(event.target as HTMLInputElement).value;
    this.currentFrame = val;
    this.frameSelected.emit(this.currentFrame);
  }

  toggleOverlay() {
    this.showOverlay = !this.showOverlay;
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyboard(event: KeyboardEvent) {
    if (event.key === 'ArrowLeft') this.prevFrame();
    if (event.key === 'ArrowRight') this.nextFrame();
  }
}
