import { Component, Input, OnChanges, SimpleChanges, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, DiameterResult } from '../../services/api';

@Component({
  selector: 'app-diameter',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './diameter.html',
  styleUrl: './diameter.css',
})
export class DiameterComponent implements OnChanges {
  @Input() jobId = '';
  @Input() frameIndex = 0;

  pixelScale = 0.03378;
  result: DiameterResult | null = null;
  loading = false;
  error = '';

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['frameIndex'] || changes['jobId']) {
      this.result = null;
      this.error = '';
    }
  }

  measure() {
    if (!this.jobId) return;
    this.loading = true;
    this.error = '';
    this.result = null;
    this.cdr.detectChanges();

    this.api.getDiameter(this.jobId, this.frameIndex, this.pixelScale).subscribe({
      next: (res) => {
        this.result = res;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = err.error?.detail || 'No mask found for this frame';
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  get maskUrl(): string {
    return this.api.getMaskUrl(this.jobId, this.frameIndex);
  }

  get isAneurysm(): boolean {
    return !!this.result && this.result.diameter_cm >= 3.0;
  }
}
