import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { InventoryService } from '../../services/inventory.service';
import { InventorySession } from '../../interfaces/InventorySession';
import { InventoryColor } from '../../interfaces/InventoryColor';
import { InventorySessionItem } from '../../interfaces/InventorySessionItem';
import { InventoryDiff } from '../../interfaces/InventoryDiff';

type ViewState = 'loading' | 'landing' | 'colors' | 'review' | 'add-card' | 'diff' | 'done';

const PAGE_SIZE = 50;

@Component({
  selector: 'app-inventory-audit',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './inventory-audit.html',
  styleUrl: './inventory-audit.css',
})
export class InventoryAudit implements OnInit {
  view: ViewState = 'loading';
  session: InventorySession | null = null;
  errorMessage = '';

  colors: InventoryColor[] = [];
  selectedColor: InventoryColor | null = null;

  items: InventorySessionItem[] = [];
  itemsTotal = 0;
  page = 1;
  showReviewed = false;
  searchTerm = '';

  editingCode: string | null = null;
  editingQuantity: number | null = null;

  newCardCode = '';
  newCardPreview: any = null;
  newCardQuantity: number | null = null;
  newCardError = '';
  newCardLoading = false;

  diff: InventoryDiff | null = null;
  applyResult: { updated: number; added: number; left_pending: number } | null = null;

  constructor(private inventoryService: InventoryService, private router: Router) {}

  ngOnInit(): void {
    this.loadCurrentSession();
  }

  private extractError(err: unknown): string {
    if (err instanceof HttpErrorResponse) {
      return err.error?.error || 'Erro inesperado ao comunicar com o servidor.';
    }
    return 'Erro inesperado.';
  }

  loadCurrentSession(): void {
    this.view = 'loading';
    this.inventoryService.getCurrentSession().subscribe({
      next: ({ session }) => {
        this.session = session;
        this.view = 'landing';
      },
      error: (err) => {
        this.errorMessage = this.extractError(err);
        this.view = 'landing';
      },
    });
  }

  startNewSession(): void {
    if (this.session && this.session.status === 'open') {
      const confirmed = confirm(
        'Isso vai descartar o progresso não aplicado da auditoria atual. Continuar?'
      );
      if (!confirmed) {
        return;
      }
    }

    this.errorMessage = '';
    this.inventoryService.startSession().subscribe({
      next: () => this.loadCurrentSessionThenGoToColors(),
      error: (err) => (this.errorMessage = this.extractError(err)),
    });
  }

  continueSession(): void {
    if (!this.session) {
      return;
    }
    this.view = 'colors';
    this.loadColors();
  }

  private loadCurrentSessionThenGoToColors(): void {
    this.inventoryService.getCurrentSession().subscribe({
      next: ({ session }) => {
        this.session = session;
        this.view = 'colors';
        this.loadColors();
      },
      error: (err) => (this.errorMessage = this.extractError(err)),
    });
  }

  loadColors(): void {
    if (!this.session) {
      return;
    }
    this.inventoryService.getColors(this.session.id).subscribe({
      next: (colors) => (this.colors = colors),
      error: (err) => (this.errorMessage = this.extractError(err)),
    });
  }

  selectColor(color: InventoryColor): void {
    this.selectedColor = color;
    this.view = 'review';
    this.page = 1;
    this.showReviewed = false;
    this.searchTerm = '';
    this.editingCode = null;
    this.loadItems();
  }

  loadItems(): void {
    if (!this.session || !this.selectedColor) {
      return;
    }
    this.inventoryService
      .getItems(this.session.id, {
        color: this.selectedColor.card_color,
        status: this.showReviewed ? 'reviewed' : 'pending',
        search: this.searchTerm,
        page: this.page,
        pageSize: PAGE_SIZE,
      })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.itemsTotal = result.total;
        },
        error: (err) => (this.errorMessage = this.extractError(err)),
      });
  }

  onSearch(): void {
    this.page = 1;
    this.loadItems();
  }

  toggleShowReviewed(): void {
    this.showReviewed = !this.showReviewed;
    this.page = 1;
    this.editingCode = null;
    this.loadItems();
  }

  nextPage(): void {
    if (this.page * PAGE_SIZE >= this.itemsTotal) {
      return;
    }
    this.page += 1;
    this.loadItems();
  }

  prevPage(): void {
    if (this.page <= 1) {
      return;
    }
    this.page -= 1;
    this.loadItems();
  }

  private applyLocalReviewCount(): void {
    if (this.selectedColor) {
      this.selectedColor.reviewed += 1;
      this.selectedColor.pending -= 1;
    }
    if (this.session) {
      this.session.reviewed_count += 1;
      this.session.pending_count -= 1;
    }
  }

  markUnchanged(item: InventorySessionItem): void {
    if (!this.session) {
      return;
    }
    this.inventoryService.reviewItem(this.session.id, item.code, false).subscribe({
      next: () => {
        if (!this.showReviewed) {
          this.items = this.items.filter((i) => i.code !== item.code);
        }
        this.applyLocalReviewCount();
      },
      error: (err) => (this.errorMessage = this.extractError(err)),
    });
  }

  openEditQuantity(item: InventorySessionItem): void {
    this.editingCode = item.code;
    this.editingQuantity = item.system_quantity;
  }

  cancelEditQuantity(): void {
    this.editingCode = null;
    this.editingQuantity = null;
  }

  confirmChangedQuantity(item: InventorySessionItem): void {
    if (!this.session) {
      return;
    }
    if (this.editingQuantity === null || this.editingQuantity < 0 || !Number.isInteger(this.editingQuantity)) {
      this.errorMessage = 'Digite uma quantidade válida (inteiro maior ou igual a 0).';
      return;
    }

    this.inventoryService.reviewItem(this.session.id, item.code, true, this.editingQuantity).subscribe({
      next: () => {
        if (!this.showReviewed) {
          this.items = this.items.filter((i) => i.code !== item.code);
        }
        this.applyLocalReviewCount();
        this.editingCode = null;
        this.editingQuantity = null;
      },
      error: (err) => (this.errorMessage = this.extractError(err)),
    });
  }

  backToColors(): void {
    this.view = 'colors';
    this.selectedColor = null;
    this.loadColors();
  }

  openAddCard(): void {
    this.view = 'add-card';
    this.newCardCode = '';
    this.newCardPreview = null;
    this.newCardQuantity = null;
    this.newCardError = '';
  }

  lookupNewCard(): void {
    const code = this.newCardCode.trim().toUpperCase();
    if (!code) {
      this.newCardError = 'Digite um código.';
      return;
    }
    this.newCardError = '';
    this.newCardPreview = null;
    this.newCardLoading = true;

    this.inventoryService.lookupCard(code).subscribe({
      next: (card) => {
        this.newCardPreview = card;
        this.newCardLoading = false;
      },
      error: (err) => {
        this.newCardError = this.extractError(err);
        this.newCardLoading = false;
      },
    });
  }

  confirmAddNewCard(): void {
    if (!this.session || !this.newCardPreview) {
      return;
    }
    if (this.newCardQuantity === null || this.newCardQuantity < 1 || !Number.isInteger(this.newCardQuantity)) {
      this.newCardError = 'Digite uma quantidade válida (inteiro maior ou igual a 1).';
      return;
    }

    const code = this.newCardCode.trim().toUpperCase();
    this.inventoryService.addNewCard(this.session.id, code, this.newCardQuantity).subscribe({
      next: () => {
        this.view = 'colors';
        this.loadColors();
        this.loadCurrentSessionSummaryOnly();
      },
      error: (err) => (this.newCardError = this.extractError(err)),
    });
  }

  private loadCurrentSessionSummaryOnly(): void {
    this.inventoryService.getCurrentSession().subscribe({
      next: ({ session }) => (this.session = session),
    });
  }

  openDiffReview(): void {
    if (!this.session) {
      return;
    }
    this.view = 'diff';
    this.loadDiff();
  }

  loadDiff(): void {
    if (!this.session) {
      return;
    }
    this.inventoryService.getDiff(this.session.id).subscribe({
      next: (diff) => (this.diff = diff),
      error: (err) => (this.errorMessage = this.extractError(err)),
    });
  }

  confirmApply(): void {
    if (!this.session || !this.diff) {
      return;
    }

    const nothingToApply = this.diff.updates.length === 0 && this.diff.new_cards.length === 0;
    if (nothingToApply) {
      const confirmed = confirm('Nenhuma mudança será aplicada. Mesmo assim encerrar esta auditoria?');
      if (!confirmed) {
        return;
      }
    }

    this.inventoryService.applySession(this.session.id).subscribe({
      next: (result) => {
        this.applyResult = result;
        this.view = 'done';
      },
      error: (err) => (this.errorMessage = this.extractError(err)),
    });
  }

  goToLibrary(): void {
    this.router.navigate(['/library']);
  }
}
