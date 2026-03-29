import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ReviewBadge } from '../review-badge/review-badge';
import { ReviewService } from '../../services/review.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink, ReviewBadge],
  templateUrl: './home.html',
  styleUrl: './home.css',
})
export class Home implements OnInit {
  reviewQuantity = 0;

  constructor(private reviewService: ReviewService) {}

  ngOnInit(): void {
    this.reviewService.loadCards();
    this.reviewService.getCardToReview().subscribe({
      next: (cards) => {
        this.reviewQuantity = Array.isArray(cards) ? cards.length : 1;
      },
      error: () => {
        this.reviewQuantity = 1;
      },
    });
  }
}
