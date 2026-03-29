import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { ReviewService } from '../../services/review.service';

@Component({
  selector: 'app-review-badge',
  imports: [CommonModule, RouterModule],
  standalone: true,
  templateUrl: './review-badge.html',
  styleUrl: './review-badge.css',
})
export class ReviewBadge  {
   @Input() quantity: number = 0;
}
