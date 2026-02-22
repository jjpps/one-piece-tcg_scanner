import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LibraryService } from '../services/library.service';
import { LibraryCard } from '../../interfaces/cards.mode';

@Component({
  selector: 'app-library-component',
  imports: [CommonModule],
  templateUrl: './library-component.html',
  styleUrl: './library-component.css',
})
export class LibraryComponent  implements OnInit  {
   cards: LibraryCard[] = [];
  loading = true;
  error: string | null = null;

  constructor(private libraryService: LibraryService, private cdr: ChangeDetectorRef,) {}

  ngOnInit(): void {
    this.loadLibrary();
  }
  loadLibrary(): void {
    this.loading = true;

    this.libraryService.getLibrary().subscribe({
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

}
