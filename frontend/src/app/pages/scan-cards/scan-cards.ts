

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProcessingBar } from '../processing-bar/processing-bar';
import { UploadCards } from '../upload-cards/upload-cards';
import { CardsReview } from '../cards-review/cards-review';
@Component({
  selector: 'app-scan-cards',
  standalone: true,
  imports: [ProcessingBar, UploadCards, CardsReview, CommonModule],
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

  // methods to move between stages
  proceedToReview(): void {
    this.stage = 'review';
  }

  reset(): void {
    this.stage = 'upload';
  }
}
