import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs';
import { ReviewService } from '../../services/review.service';

@Component({
  selector: 'app-mega-menu',
  imports: [RouterLink],
  templateUrl: './mega-menu.html',
  styleUrl: './mega-menu.css',
})
export class MegaMenu {
  private reviewService = inject(ReviewService);
  private router = inject(Router);

  collapsed = signal(true);
  openGroup = signal<string | null>(null);
  reviewQuantity = toSignal(this.reviewService.getCardToReview(), { initialValue: [] });

  constructor() {
    this.reviewService.loadCards();
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .subscribe(() => {
        this.collapsed.set(true);
        this.openGroup.set(null);
        this.reviewService.loadCards();
      });
  }

  toggleGroup(name: string): void {
    this.openGroup.update((g) => (g === name ? null : name));
  }
}
