import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LibraryService, LibraryPage, LIBRARY_PAGE_SIZE } from '../../services/library.service';
import { catchError, combineLatest, Observable, of, startWith, Subject, BehaviorSubject, switchMap, tap } from 'rxjs';
import { LibraryCard } from '../../interfaces/LibraryCard';

const EMPTY_PAGE: LibraryPage = { items: [], total: 0, page: 1, page_size: LIBRARY_PAGE_SIZE };

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './library.html',
  styleUrl: './library.css',
})
export class Library {
  libraryState$!: Observable<LibraryPage>;
  cardColors$!: Observable<string[]>;
  searchBy = 'code';
  searchTerm = '';
  selectedColor = '';
  page = 1;
  total = 0;
  readonly pageSize = LIBRARY_PAGE_SIZE;

  private refresh$ = new Subject<void>();
  private searchBy$ = new BehaviorSubject<string>(this.searchBy);
  private searchTerm$ = new BehaviorSubject<string>(this.searchTerm);
  private selectedColor$ = new BehaviorSubject<string>(this.selectedColor);
  private page$ = new BehaviorSubject<number>(this.page);

  constructor(private libraryService: LibraryService) {
    this.libraryState$ = combineLatest([
      this.refresh$.pipe(startWith(void 0)),
      this.searchBy$,
      this.searchTerm$,
      this.selectedColor$,
      this.page$,
    ]).pipe(
      switchMap(([, searchBy, searchTerm, color, page]) =>
        this.libraryService
          .getLibrary({ searchBy, search: searchTerm, color, page })
          .pipe(
            catchError((err) => {
              console.error('Erro ao carregar biblioteca', err);
              return of(EMPTY_PAGE);
            })
          )
      ),
      tap((result) => (this.total = result.total))
    );

    this.cardColors$ = this.refresh$.pipe(
      startWith(void 0),
      switchMap(() =>
        this.libraryService.getCardColors().pipe(
          catchError((err) => {
            console.error('Erro ao carregar cores da biblioteca', err);
            return of([]);
          })
        )
      )
    );
  }

  trackByCode(_: number, card: LibraryCard) {
    return card.code;
  }

  search() {
    this.goToPage(1);
    this.searchBy$.next(this.searchBy);
    this.searchTerm$.next(this.searchTerm);
  }

  onColorChange(color: string) {
    this.selectedColor = color;
    this.goToPage(1);
    this.selectedColor$.next(this.selectedColor);
  }

  get hasNextPage(): boolean {
    return this.page * this.pageSize < this.total;
  }

  nextPage() {
    if (!this.hasNextPage) return;
    this.goToPage(this.page + 1);
  }

  prevPage() {
    if (this.page <= 1) return;
    this.goToPage(this.page - 1);
  }

  private goToPage(page: number) {
    if (this.page === page) return;
    this.page = page;
    this.page$.next(page);
  }

  addCard(code: string) {
    this.libraryService.addCardQuantity(code).subscribe({
      next: () => this.refresh$.next(),
      error: (err) => console.error('Erro ao adicionar carta', err),
    });
  }

  removeCard(code: string) {
    this.libraryService.removeCardQuantity(code).subscribe({
      next: () => this.refresh$.next(),
      error: (err) => console.error('Erro ao remover carta', err),
    });
  }
}
