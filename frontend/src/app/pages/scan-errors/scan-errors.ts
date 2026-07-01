import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { LibraryService } from '../../services/library.service';
import { catchError, Observable, of, startWith, Subject, switchMap } from 'rxjs';

@Component({
  selector: 'app-scan-errors',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './scan-errors.html',
  styleUrls: ['./scan-errors.css'],
})
export class ScanErrors {

  private refresh$ = new Subject<void>();

  cardsNotDetected$: Observable<any>;

  activeZoomCardId: string | number | null = null;
  zoomActive = false;
  zoomImageSrc: string | null = null;
  zoomStyle: { [klass: string]: string } = {};
  zoomScale = 3;

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

  onImageMouseEnter(imageUrl: string, cardId: string | number, event: MouseEvent): void {
    this.activeZoomCardId = cardId;
    this.zoomActive = true;
    this.zoomImageSrc = imageUrl;
    this.updateZoomStyle(event);
  }

  onImageMouseMove(event: MouseEvent): void {
    if (!this.zoomActive || !this.zoomImageSrc || this.activeZoomCardId === null) {
      return;
    }

    this.updateZoomStyle(event);
  }

  onImageMouseLeave(): void {
    this.zoomActive = false;
    this.activeZoomCardId = null;
    this.zoomImageSrc = null;
    this.zoomStyle = {};
  }

  private updateZoomStyle(event: MouseEvent): void {
    const currentTarget = event.currentTarget as HTMLElement | null;
    if (!currentTarget || !this.zoomImageSrc) {
      return;
    }

    const rect = currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const positionX = Math.max(0, Math.min(100, (x / rect.width) * 100));
    const positionY = Math.max(0, Math.min(100, (y / rect.height) * 100));

    this.zoomStyle = {
      'background-image': `url(${this.zoomImageSrc})`,
      'background-position': `${positionX}% ${positionY}%`,
      'background-size': `${rect.width * this.zoomScale}px ${rect.height * this.zoomScale}px`,
    };
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