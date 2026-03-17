

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ProcessingBar } from '../processing-bar/processing-bar';
import { UploadCards } from '../upload-cards/upload-cards';
@Component({
  selector: 'app-scan-cards',
  standalone: true,
  imports: [ProcessingBar, UploadCards, CommonModule],
  templateUrl: './scan-cards.html',
  styleUrl: './scan-cards.css',
})
export class ScanCards {
  // internal state can be an enum/string to simplify visibility logic
  private stage: 'upload' | 'review' = 'upload';

  // getters provide a clean way to bind in the template
  get showCardsUpload(): boolean {
    return this.stage === 'upload';
  }

  get showCardsReview(): boolean {
    return this.stage === 'review';
  }

  constructor(private router: Router) {}

  // methods to move between stages
  proceedToReview(): void {
    this.router.navigate(['/home']);
  }

  reset(): void {
    this.stage = 'upload';
  }
}
