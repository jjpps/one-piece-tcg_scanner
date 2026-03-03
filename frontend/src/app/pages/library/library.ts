import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { LibraryService } from '../../services/library.service';
import { catchError, Observable, of, startWith } from 'rxjs';

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './library.html',
  styleUrl: './library.css',
})
export class Library {
 libraryState$!: Observable<any>;

  constructor(private libraryService: LibraryService) {
    this.libraryState$ = this.libraryService.getLibrary().pipe(
      startWith(null), // indica loading inicial
      catchError((err) => {
        console.error('Erro ao carregar biblioteca', err);
        return of([]); // retorna array vazio em caso de erro
      })
    );
  }
}
