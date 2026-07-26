import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Component } from '@angular/core';
import { LibraryService } from '../../services/library.service';
import { catchError, Observable, of, startWith, Subject, switchMap } from 'rxjs';
import { lastValueFrom } from 'rxjs';

@Component({
  selector: 'app-scan-errors',
  standalone: true,
  imports: [CommonModule, FormsModule],
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
  selectedIds = new Set<string | number>();
  cardStates: { [id: string]: { state: 'idle' | 'pending' | 'success' | 'error'; message?: string } } = {};
  globalCode = '';
  applying = false;
  cardInputs: { [id: string]: string } = {};

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

  toggleSelection(cardId: string | number): void {
    const key = String(cardId);
    if (this.selectedIds.has(cardId)) {
      this.selectedIds.delete(cardId);
      delete this.cardStates[key];
    } else {
      this.selectedIds.add(cardId);
      this.cardStates[key] = { state: 'idle' };
    }
  }

  onKeyToggle(event: KeyboardEvent, cardId: string | number): void {
    const code = event.code || '';
    if (code === 'Space' || code === 'Enter' || code === 'Spacebar') {
      event.preventDefault();
      this.toggleSelection(cardId);
    }
  }

  getSelectedCount(): number {
    return this.selectedIds.size;
  }

  getSelectedIds(): Array<string | number> {
    return Array.from(this.selectedIds);
  }

  async applyCodeToSelected(): Promise<void> {
    const code = (this.globalCode || '').trim();
    if (!code) {
      alert('Por favor, digite o código da carta');
      return;
    }

    if (this.selectedIds.size === 0) {
      return;
    }

    this.applying = true;
    const ids = this.getSelectedIds();
    let successCount = 0;
    let failCount = 0;

    for (const id of ids) {
      const key = String(id);
      this.cardStates[key] = { state: 'pending' };
      try {
        await lastValueFrom(this.libraryService.saveCardManually(String(id), code));
        this.cardStates[key] = { state: 'success' };
        successCount++;
      } catch (err: any) {
        console.error('Erro ao atualizar carta', id, err);
        this.cardStates[key] = { state: 'error', message: err?.message || 'Erro desconhecido' };
        failCount++;
      }
    }

    this.applying = false;
    //alert(`Operação finalizada: ${successCount} atualizadas, ${failCount} falharam.`);
    // limpar input global e seleção
    this.globalCode = '';
    this.selectedIds.clear();
    // limpar inputs individuais relacionados às cartas processadas
    for (const id of ids) {
      const key = String(id);
      this.cardInputs[key] = '';
    }
    // requisitar refresh da lista (recarrega os dados)
    this.refresh$.next();
  }

  async retryCard(cardId: string | number): Promise<void> {
    const key = String(cardId);
    const code = (this.globalCode || '').trim();
    if (!code) {
      alert('Por favor, digite o código antes de re-tentar');
      return;
    }
    this.cardStates[key] = { state: 'pending' };
    try {
      await lastValueFrom(this.libraryService.saveCardManually(String(cardId), code));
      this.cardStates[key] = { state: 'success' };
    } catch (err: any) {
      this.cardStates[key] = { state: 'error', message: err?.message || 'Erro desconhecido' };
    }
  }

  // saveCard already exists below; ensure it uses cardInputs when provided

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