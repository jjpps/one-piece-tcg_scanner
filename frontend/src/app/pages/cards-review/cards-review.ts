import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ReviewService } from '../../services/review.service';
import { LibraryCard } from '../../interfaces/LibraryCard';

@Component({
  selector: 'app-cards-review',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cards-review.html',
  styleUrl: './cards-review.css',
})
export class CardsReview implements OnInit {

  reviewState$!: Observable<LibraryCard[]>;

  constructor(private reviewService: ReviewService) {
    this.reviewState$ = this.reviewService.getCardToReview().pipe(
      catchError((err) => {
        console.error('Erro ao carregar biblioteca', err);
        return of([]);
      })
    );
  }

  ngOnInit(): void {
    this.reviewService.loadCards();
  }

  approve(card: LibraryCard) {
    this.reviewService.approveCard(card).subscribe({
      next: () => {
        console.log('Carta aprovada com sucesso');
        this.reviewService.loadCards();
      },
      error: (err) => {
        console.error('Erro ao aprovar carta', err);
        alert('Erro ao aprovar a carta. Tente novamente.');
      },
    });
  }

  reject(card: LibraryCard) {
    this.reviewService.reproveCard(card).subscribe({
      next: () => {
        console.log('Carta reprovada com sucesso');
        this.reviewService.loadCards();
      },
      error: (err) => {
        console.error('Erro ao reprovar carta', err);
        alert('Erro ao reprovar a carta. Tente novamente.');
      },
    });
  }
}
