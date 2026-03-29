import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LibraryService } from '../../services/library.service';
import { catchError, combineLatest, map, Observable, of, startWith, Subject, BehaviorSubject, switchMap } from 'rxjs';
import { LibraryCard } from '../../interfaces/LibraryCard';

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './library.html',
  styleUrl: './library.css',
})
export class Library {
  libraryState$!: Observable<LibraryCard[]>;
  searchBy = 'code';
  searchTerm = '';
  private refresh$ = new Subject<void>();
  private searchBy$ = new BehaviorSubject<string>(this.searchBy);
  private searchTerm$ = new BehaviorSubject<string>(this.searchTerm);

  constructor(private libraryService: LibraryService) {
    const library$ = this.refresh$.pipe(
      startWith(void 0),
      switchMap(() =>
        this.libraryService.getLibrary().pipe(
          catchError((err) => {
            console.error('Erro ao carregar biblioteca', err);
            return of([]);
          })
        )
      )
    );

    this.libraryState$ = combineLatest([library$, this.searchBy$, this.searchTerm$]).pipe(
      map(([cards, searchBy, searchTerm]) => {
        const term = searchTerm?.trim().toLowerCase();
        if (!term) {
          return cards;
        }

        return cards.filter((card) => {
          const value =
            searchBy === 'name'
              ? card.card_name
              : card.code;
          return value?.toString().toLowerCase().includes(term);
        });
      })
    );
  }

  search() {
    this.searchBy$.next(this.searchBy);
    this.searchTerm$.next(this.searchTerm);
  }

  addCard(code: string) {
    console.log('Adicionar carta:', code);
    this.libraryService.addCardQuantity(code).subscribe({
      next: () => this.refresh$.next(),
      error: (err) => console.error('Erro ao adicionar carta', err),
    });
  }

  removeCard(code: string) {
    console.log('Remover carta:', code);
    this.libraryService.removeCardQuantity(code).subscribe({
      next: () => this.refresh$.next(),
      error: (err) => console.error('Erro ao remover carta', err),
    });
  }
}
