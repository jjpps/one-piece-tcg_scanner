import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { LibraryService } from '../../services/library.service';
import { catchError, Observable, of, startWith, Subject, switchMap } from 'rxjs';

@Component({
  selector: 'app-scan-errors',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './scan-errors.html',
  styleUrl: './scan-errors.css',
})
export class ScanErrors {

  private refresh$ = new Subject<void>();

  cardsNotDetected$: Observable<any>;

  constructor(private libraryService: LibraryService) {

    this.cardsNotDetected$ = this.refresh$.pipe(
      startWith(void 0), 
      switchMap(() =>
        this.libraryService.getScanErrors().pipe(
          catchError((err) => {
            console.error('Erro ao carregar biblioteca', err);
            return of([]);
          })
        )
      )
    );
  }

  saveCard(fileName: string, inputValue: string): void {

    if (!inputValue.trim()) {
      alert('Por favor, digite o código da carta');
      return;
    }

    this.libraryService.saveCardManually(fileName, inputValue).subscribe({
      next: () => {
        console.log('Carta salva com sucesso');
        this.refresh$.next(); 
      },
      error: (err) => {
        console.error('Erro ao salvar carta', err);
        alert('Erro ao salvar a carta. Tente novamente.');
      },
    });
  }
}