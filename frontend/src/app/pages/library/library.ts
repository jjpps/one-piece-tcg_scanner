import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { LibraryService } from '../../services/library.service';
import { catchError, Observable, of, startWith, Subject, switchMap } from 'rxjs';

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './library.html',
  styleUrl: './library.css',
})
export class Library {
  libraryState$!: Observable<any>;
  private refresh$ = new Subject<void>();

  constructor(private libraryService: LibraryService) {
    this.libraryState$ = this.refresh$.pipe(
      startWith(void 0),
      switchMap(() =>
        this.libraryService.getLibrary().pipe(
          catchError((err) => {
            console.error('Erro ao carregar biblioteca', err);
            return of([]); // retorna array vazio em caso de erro
          })
        )
      )
    );
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
