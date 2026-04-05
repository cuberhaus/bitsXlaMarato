import { Component, Input, OnChanges, SimpleChanges, ChangeDetectorRef, NgZone } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, DiameterResult, DiameterImprovedResult } from '../../services/api';

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
  @Input() method: 'original' | 'improved' = 'original';

  pixelScale = 0.03378;
  result: DiameterResult | null = null;
  resultImproved: DiameterImprovedResult | null = null;
  loading = false;
  error = '';
  showInfo = false;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef, private zone: NgZone) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['frameIndex'] || changes['jobId']) {
      this.result = null;
      this.resultImproved = null;
      this.error = '';
    }
  }

  measure() {
    if (!this.jobId) return;
    this.loading = true;
    this.error = '';
    this.result = null;
    this.resultImproved = null;

    if (this.method === 'improved') {
      this.api.getDiameterImproved(this.jobId, this.frameIndex, this.pixelScale).subscribe({
        next: (res) => {
          this.zone.run(() => {
            this.resultImproved = res;
            this.loading = false;
            this.cdr.detectChanges();
          });
        },
        error: (err) => {
          this.zone.run(() => {
            this.error = err.error?.detail || 'No mask found for this frame';
            this.loading = false;
            this.cdr.detectChanges();
          });
        },
      });
    } else {
      this.api.getDiameter(this.jobId, this.frameIndex, this.pixelScale).subscribe({
        next: (res) => {
          this.zone.run(() => {
            this.result = res;
            this.loading = false;
            this.cdr.detectChanges();
          });
        },
        error: (err) => {
          this.zone.run(() => {
            this.error = err.error?.detail || 'No mask found for this frame';
            this.loading = false;
            this.cdr.detectChanges();
          });
        },
      });
    }
  }

  get maskUrl(): string {
    return this.api.getMaskUrl(this.jobId, this.frameIndex);
  }

  get diameterCm(): number {
    if (this.method === 'improved' && this.resultImproved) return this.resultImproved.diameter_cm;
    if (this.result) return this.result.diameter_cm;
    return 0;
  }

  get diameterPx(): number {
    if (this.method === 'improved' && this.resultImproved) return this.resultImproved.diameter_px;
    if (this.result) return this.result.diameter_px;
    return 0;
  }

  get currentPixelScale(): number {
    if (this.method === 'improved' && this.resultImproved) return this.resultImproved.pixel_scale;
    if (this.result) return this.result.pixel_scale;
    return this.pixelScale;
  }

  get hasResult(): boolean {
    return this.method === 'improved' ? !!this.resultImproved : !!this.result;
  }

  get isAneurysm(): boolean {
    return this.hasResult && this.diameterCm >= 3.0;
  }
}
