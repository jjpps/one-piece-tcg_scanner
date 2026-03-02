import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { LibraryService } from '../services/library.service';
import { LibraryCard } from '../../interfaces/cards.mode';

@Component({
  selector: 'app-scan-errors',
  imports: [CommonModule],
  standalone:true,
  templateUrl: './scan-errors.html',
  styleUrl: './scan-errors.css',
})
export class ScanErrors  implements OnInit {
  cards: LibraryCard[] = [];
  loading = true;
  error: string | null = null;
  savingId: string | null = null;
  constructor(private libraryService: LibraryService, private cdr: ChangeDetectorRef) {}

    ngOnInit(): void {
    this.loadLibraryErrors();
  }

    loadLibraryErrors(): void {
    this.loading = true;

    this.libraryService.getScanErrors().subscribe({
      next: (data) => {
        this.cards = data;
        this.loading = false;
        console.log(this.cards);
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Erro ao carregar biblioteca', err);
        this.error = 'Erro ao carregar biblioteca';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });    
  }

  saveCard(fileName: string,inputValue: string): void {
    if (!inputValue.trim()) {
      alert('Por favor, digite o código da carta');
      return;
    }

    this.libraryService.saveCardManually(fileName,inputValue).subscribe({
      next: () => {
        console.log('Carta salva com sucesso');
        this.savingId = null;
        this.loadLibraryErrors();
      },
      error: (err) => {
        console.error('Erro ao salvar carta', err);
        alert('Erro ao salvar a carta. Tente novamente.');
        this.savingId = null;
        this.cdr.detectChanges();
      }
    });
  }

}
