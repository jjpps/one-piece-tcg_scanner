import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { catchError, Observable, of, startWith, Subject, switchMap } from 'rxjs';
import { ReviewService } from '../../services/review.service';
import { LibraryCard } from '../../interfaces/LibraryCard';

@Component({
  selector: 'app-cards-review',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cards-review.html',
  styleUrl: './cards-review.css',
})
export class CardsReview {

  reviewState$!: Observable<any>;
  private refresh$ = new Subject<void>();

  constructor(private reviewService:ReviewService) {
    this.reviewState$ = this.refresh$.pipe(
          startWith(void 0), 
          switchMap(() =>
            this.reviewService.getCardToReview().pipe(
              catchError((err) => {
                console.error('Erro ao carregar biblioteca', err);
                return of([]);
              })
            )
          )
        );
  }
  approve(card:LibraryCard){
    this.reviewService.approveCard(card).subscribe({
      next: () => {
        console.log('Carta aprovada com sucesso');
        this.refresh$.next(); 
      },
      error: (err) => {
        console.error('Erro ao aprovar carta', err);
        alert('Erro ao aprovar a carta. Tente novamente.');
      },
    });
  }
  reject(card:LibraryCard){
    this.reviewService.reproveCard(card).subscribe({
      next: () => {
        console.log('Carta reprovada com sucesso');
        this.refresh$.next(); 
      },
      error: (err) => {
        console.error('Erro ao reprovar carta', err);
        alert('Erro ao reprovar a carta. Tente novamente.');
      },
    });
  }
}
