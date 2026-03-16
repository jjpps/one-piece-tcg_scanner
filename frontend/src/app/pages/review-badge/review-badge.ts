import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { ReviewService } from '../../services/review.service';

@Component({
  selector: 'app-review-badge',
  imports: [CommonModule, RouterModule],
  standalone: true,
  templateUrl: './review-badge.html',
  styleUrl: './review-badge.css',
})
export class ReviewBadge implements OnInit {
  quantity: number = 0;

  constructor(private reviewService: ReviewService) {}

  ngOnInit(): void {
    this.reviewService.getCardToReview().subscribe({
      next: (cards) => {
        this.quantity = Array.isArray(cards) ? cards.length : 0;
      },
      error: () => {
        this.quantity = 0;
      },
    });
  }
}
