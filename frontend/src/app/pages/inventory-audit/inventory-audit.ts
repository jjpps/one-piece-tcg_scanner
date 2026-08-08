import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
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
  // Estado exposto como Signal: este app roda sem Zone.js, então uma mutação de
  // propriedade solta dentro de um callback de subscribe() não dispara re-render.
  view = signal<ViewState>('loading');
  session = signal<InventorySession | null>(null);
  errorMessage = signal('');

  colors = signal<InventoryColor[]>([]);
  selectedColor = signal<InventoryColor | null>(null);

  items = signal<InventorySessionItem[]>([]);
  itemsTotal = signal(0);
  page = signal(1);
  showReviewed = signal(false);
  searchTerm = signal('');

  editingCode = signal<string | null>(null);
  editingQuantity = signal<number | null>(null);

  newCardCode = signal('');
  newCardPreview = signal<any>(null);
  newCardQuantity = signal<number | null>(null);
  newCardError = signal('');
  newCardLoading = signal(false);

  diff = signal<InventoryDiff | null>(null);
  applyResult = signal<{ updated: number; added: number; left_pending: number } | null>(null);

  zoomImage = signal<{ url: string; alt: string } | null>(null);

  constructor(private inventoryService: InventoryService, private router: Router) {}

  openImageZoom(url: string | null | undefined, alt: string): void {
    if (!url) {
      return;
    }
    this.zoomImage.set({ url, alt });
  }

  closeImageZoom(): void {
    this.zoomImage.set(null);
  }

  ngOnInit(): void {
    this.loadCurrentSession();
  }

  private extractError(err: unknown): string {
    if (err instanceof HttpErrorResponse) {
      return err.error?.error || 'Erro inesperado ao comunicar com o servidor.';
    }
    return 'Erro inesperado.';
  }

  clearError(): void {
    this.errorMessage.set('');
  }

  loadCurrentSession(): void {
    this.view.set('loading');
    this.inventoryService.getCurrentSession().subscribe({
      next: ({ session }) => {
        this.session.set(session);
        this.view.set('landing');
      },
      error: (err) => {
        this.errorMessage.set(this.extractError(err));
        this.view.set('landing');
      },
    });
  }

  startNewSession(): void {
    const current = this.session();
    if (current && current.status === 'open') {
      const confirmed = confirm('Isso vai descartar o progresso não aplicado da auditoria atual. Continuar?');
      if (!confirmed) {
        return;
      }
    }

    this.errorMessage.set('');
    this.inventoryService.startSession().subscribe({
      next: () => this.loadCurrentSessionThenGoToColors(),
      error: (err) => this.errorMessage.set(this.extractError(err)),
    });
  }

  continueSession(): void {
    if (!this.session()) {
      return;
    }
    this.view.set('colors');
    this.loadColors();
  }

  private loadCurrentSessionThenGoToColors(): void {
    this.inventoryService.getCurrentSession().subscribe({
      next: ({ session }) => {
        this.session.set(session);
        this.view.set('colors');
        this.loadColors();
      },
      error: (err) => this.errorMessage.set(this.extractError(err)),
    });
  }

  loadColors(): void {
    const session = this.session();
    if (!session) {
      return;
    }
    this.inventoryService.getColors(session.id).subscribe({
      next: (colors) => this.colors.set(colors),
      error: (err) => this.errorMessage.set(this.extractError(err)),
    });
  }

  selectColor(color: InventoryColor): void {
    this.selectedColor.set(color);
    this.view.set('review');
    this.page.set(1);
    this.showReviewed.set(false);
    this.searchTerm.set('');
    this.editingCode.set(null);
    this.loadItems();
  }

  loadItems(): void {
    const session = this.session();
    const selectedColor = this.selectedColor();
    if (!session || !selectedColor) {
      return;
    }
    this.inventoryService
      .getItems(session.id, {
        color: selectedColor.card_color,
        status: this.showReviewed() ? 'reviewed' : 'pending',
        search: this.searchTerm(),
        page: this.page(),
        pageSize: PAGE_SIZE,
      })
      .subscribe({
        next: (result) => {
          this.items.set(result.items);
          this.itemsTotal.set(result.total);
        },
        error: (err) => this.errorMessage.set(this.extractError(err)),
      });
  }

  onSearchTermChange(value: string): void {
    this.searchTerm.set(value);
  }

  onSearch(): void {
    this.page.set(1);
    this.loadItems();
  }

  toggleShowReviewed(): void {
    this.showReviewed.set(!this.showReviewed());
    this.page.set(1);
    this.editingCode.set(null);
    this.loadItems();
  }

  nextPage(): void {
    if (this.page() * PAGE_SIZE >= this.itemsTotal()) {
      return;
    }
    this.page.set(this.page() + 1);
    this.loadItems();
  }

  prevPage(): void {
    if (this.page() <= 1) {
      return;
    }
    this.page.set(this.page() - 1);
    this.loadItems();
  }

  private applyLocalReviewCount(): void {
    const color = this.selectedColor();
    if (color) {
      this.selectedColor.set({ ...color, reviewed: color.reviewed + 1, pending: color.pending - 1 });
    }
    const session = this.session();
    if (session) {
      this.session.set({
        ...session,
        reviewed_count: session.reviewed_count + 1,
        pending_count: session.pending_count - 1,
      });
    }
  }

  markUnchanged(item: InventorySessionItem): void {
    const session = this.session();
    if (!session) {
      return;
    }
    this.inventoryService.reviewItem(session.id, item.code, false).subscribe({
      next: () => {
        if (!this.showReviewed()) {
          this.items.set(this.items().filter((i) => i.code !== item.code));
        }
        this.applyLocalReviewCount();
      },
      error: (err) => this.errorMessage.set(this.extractError(err)),
    });
  }

  openEditQuantity(item: InventorySessionItem): void {
    this.editingCode.set(item.code);
    this.editingQuantity.set(item.system_quantity);
  }

  cancelEditQuantity(): void {
    this.editingCode.set(null);
    this.editingQuantity.set(null);
  }

  onEditingQuantityChange(value: number): void {
    this.editingQuantity.set(value);
  }

  confirmChangedQuantity(item: InventorySessionItem): void {
    const session = this.session();
    if (!session) {
      return;
    }
    const quantity = this.editingQuantity();
    if (quantity === null || quantity < 0 || !Number.isInteger(quantity)) {
      this.errorMessage.set('Digite uma quantidade válida (inteiro maior ou igual a 0).');
      return;
    }

    this.inventoryService.reviewItem(session.id, item.code, true, quantity).subscribe({
      next: () => {
        if (!this.showReviewed()) {
          this.items.set(this.items().filter((i) => i.code !== item.code));
        }
        this.applyLocalReviewCount();
        this.editingCode.set(null);
        this.editingQuantity.set(null);
      },
      error: (err) => this.errorMessage.set(this.extractError(err)),
    });
  }

  backToColors(): void {
    this.view.set('colors');
    this.selectedColor.set(null);
    this.loadColors();
  }

  openAddCard(): void {
    this.view.set('add-card');
    this.newCardCode.set('');
    this.newCardPreview.set(null);
    this.newCardQuantity.set(null);
    this.newCardError.set('');
  }

  onNewCardCodeChange(value: string): void {
    this.newCardCode.set(value);
  }

  onNewCardQuantityChange(value: number): void {
    this.newCardQuantity.set(value);
  }

  lookupNewCard(): void {
    const code = this.newCardCode().trim().toUpperCase();
    if (!code) {
      this.newCardError.set('Digite um código.');
      return;
    }
    this.newCardError.set('');
    this.newCardPreview.set(null);
    this.newCardLoading.set(true);

    this.inventoryService.lookupCard(code).subscribe({
      next: (card) => {
        this.newCardPreview.set(card);
        this.newCardLoading.set(false);
      },
      error: (err) => {
        this.newCardError.set(this.extractError(err));
        this.newCardLoading.set(false);
      },
    });
  }

  confirmAddNewCard(): void {
    const session = this.session();
    if (!session || !this.newCardPreview()) {
      return;
    }
    const quantity = this.newCardQuantity();
    if (quantity === null || quantity < 1 || !Number.isInteger(quantity)) {
      this.newCardError.set('Digite uma quantidade válida (inteiro maior ou igual a 1).');
      return;
    }

    const code = this.newCardCode().trim().toUpperCase();
    this.inventoryService.addNewCard(session.id, code, quantity).subscribe({
      next: () => {
        this.view.set('colors');
        this.loadColors();
        this.loadCurrentSessionSummaryOnly();
      },
      error: (err) => this.newCardError.set(this.extractError(err)),
    });
  }

  private loadCurrentSessionSummaryOnly(): void {
    this.inventoryService.getCurrentSession().subscribe({
      next: ({ session }) => this.session.set(session),
    });
  }

  openDiffReview(): void {
    if (!this.session()) {
      return;
    }
    this.view.set('diff');
    this.loadDiff();
  }

  loadDiff(): void {
    const session = this.session();
    if (!session) {
      return;
    }
    this.inventoryService.getDiff(session.id).subscribe({
      next: (diff) => this.diff.set(diff),
      error: (err) => this.errorMessage.set(this.extractError(err)),
    });
  }

  confirmApply(): void {
    const session = this.session();
    const diff = this.diff();
    if (!session || !diff) {
      return;
    }

    const nothingToApply = diff.updates.length === 0 && diff.new_cards.length === 0;
    if (nothingToApply) {
      const confirmed = confirm('Nenhuma mudança será aplicada. Mesmo assim encerrar esta auditoria?');
      if (!confirmed) {
        return;
      }
    }

    this.inventoryService.applySession(session.id).subscribe({
      next: (result) => {
        this.applyResult.set(result);
        this.view.set('done');
      },
      error: (err) => this.errorMessage.set(this.extractError(err)),
    });
  }

  goToLibrary(): void {
    this.router.navigate(['/library']);
  }
}
