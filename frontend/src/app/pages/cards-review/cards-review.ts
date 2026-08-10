import { Component, CUSTOM_ELEMENTS_SCHEMA, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ReviewService } from '../../services/review.service';
import { LocalCard } from '../../interfaces/LocalCard';
import 'img-comparison-slider';

@Component({
  selector: 'app-cards-review',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cards-review.html',
  styleUrl: './cards-review.css',
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class CardsReview implements OnInit {

  reviewState$!: Observable<LocalCard[]>;

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

  approve(card: LocalCard) {
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

  reject(card: LocalCard) {
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
