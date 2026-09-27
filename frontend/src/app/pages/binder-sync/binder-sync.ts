import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import {
  BinderSyncService,
  SyncCommitResult,
  SyncItem,
  SyncKind,
  SyncResolution,
  SyncSession,
} from '../../services/binder-sync.service';

type ViewState = 'loading' | 'landing' | 'review' | 'done';

const PAGE_SIZE = 50;

export const KIND_LABELS: Record<SyncKind, string> = {
  binder_only: 'Só no Binder',
  ours_only: 'Só no nosso',
  both: 'Quantidades diferentes',
};

export const RESOLUTION_LABELS: Record<SyncResolution, string> = {
  binder: 'Binder vence',
  ours: 'Nosso vence',
  ignore: 'Ignorar',
};

@Component({
  selector: 'app-binder-sync',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './binder-sync.html',
  styleUrl: './binder-sync.css',
})
export class BinderSync implements OnInit {
  // Signals: o app roda sem Zone.js (ver inventory-audit).
  view = signal<ViewState>('loading');
  session = signal<SyncSession | null>(null);
  errorMessage = signal('');
  csvErrors = signal<string[]>([]);
  selectedFile = signal<File | null>(null);
  busy = signal(false);

  items = signal<SyncItem[]>([]);
  itemsTotal = signal(0);
  page = signal(1);
  kindFilter = signal<SyncKind | ''>('');
  colorFilter = signal('');
  statusFilter = signal<'pending' | 'resolved' | ''>('pending');
  searchTerm = signal('');

  result = signal<SyncCommitResult | null>(null);
  copied = signal(false);

  readonly kinds = Object.keys(KIND_LABELS) as SyncKind[];
  readonly resolutions = Object.keys(RESOLUTION_LABELS) as SyncResolution[];
  readonly kindLabels = KIND_LABELS;
  readonly resolutionLabels = RESOLUTION_LABELS;
  readonly pageSize = PAGE_SIZE;

  constructor(private syncService: BinderSyncService) {}

  ngOnInit(): void {
    this.loadSession(false);
  }

  private extractError(err: unknown): string {
    if (err instanceof HttpErrorResponse) {
      this.csvErrors.set(err.error?.errors ?? []);
      return err.error?.error || 'Erro inesperado ao comunicar com o servidor.';
    }
    return 'Erro inesperado.';
  }

  private fail(err: unknown): void {
    this.errorMessage.set(this.extractError(err));
    this.busy.set(false);
  }

  clearError(): void {
    this.errorMessage.set('');
    this.csvErrors.set([]);
  }

  loadSession(goToReview: boolean): void {
    this.syncService.getCurrentSession().subscribe({
      next: ({ session }) => {
        this.session.set(session);
        if (goToReview && session) {
          this.view.set('review');
          this.loadItems();
        } else if (this.view() === 'loading') {
          this.view.set('landing');
        }
      },
      error: (err) => {
        this.fail(err);
        this.view.set('landing');
      },
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile.set(input.files?.[0] ?? null);
  }

  importCsv(): void {
    const file = this.selectedFile();
    if (!file) {
      return;
    }
    this.clearError();
    this.busy.set(true);
    this.syncService.importCsv(file).subscribe({
      next: () => {
        this.busy.set(false);
        this.loadSession(true);
      },
      error: (err) => this.fail(err),
    });
  }

  continueSession(): void {
    this.view.set('review');
    this.loadItems();
  }

  discardSession(): void {
    const session = this.session();
    if (!session || !confirm('Descartar esta sincronização? Nenhuma mudança será aplicada.')) {
      return;
    }
    this.syncService.discard(session.id).subscribe({
      next: () => {
        this.session.set(null);
        this.selectedFile.set(null);
        this.view.set('landing');
      },
      error: (err) => this.fail(err),
    });
  }

  loadItems(): void {
    const session = this.session();
    if (!session) {
      return;
    }
    this.syncService
      .getItems(session.id, {
        kind: this.kindFilter(),
        color: this.colorFilter(),
        status: this.statusFilter(),
        search: this.searchTerm(),
        page: this.page(),
        pageSize: PAGE_SIZE,
      })
      .subscribe({
        next: (res) => {
          this.items.set(res.items);
          this.itemsTotal.set(res.total);
        },
        error: (err) => this.fail(err),
      });
  }

  applyFilters(): void {
    this.page.set(1);
    this.loadItems();
  }

  setKindFilter(value: SyncKind | ''): void {
    this.kindFilter.set(value);
    this.applyFilters();
  }

  setColorFilter(value: string): void {
    this.colorFilter.set(value);
    this.applyFilters();
  }

  setStatusFilter(value: 'pending' | 'resolved' | ''): void {
    this.statusFilter.set(value);
    this.applyFilters();
  }

  onSearchTermChange(value: string): void {
    this.searchTerm.set(value);
  }

  nextPage(): void {
    if (this.page() * PAGE_SIZE < this.itemsTotal()) {
      this.page.set(this.page() + 1);
      this.loadItems();
    }
  }

  prevPage(): void {
    if (this.page() > 1) {
      this.page.set(this.page() - 1);
      this.loadItems();
    }
  }

  private refresh(): void {
    this.loadSession(false);
    this.loadItems();
  }

  resolve(item: SyncItem, resolution: SyncResolution): void {
    const session = this.session();
    if (!session) {
      return;
    }
    // Clicar na resolução já escolhida volta o item para pendente.
    const next = item.resolution === resolution ? null : resolution;
    this.syncService.resolveItem(session.id, item.code, next).subscribe({
      next: () => this.refresh(),
      error: (err) => this.fail(err),
    });
  }

  resolveBulk(resolution: SyncResolution): void {
    const session = this.session();
    if (!session) {
      return;
    }
    this.syncService.resolveBulk(session.id, resolution, this.kindFilter(), this.colorFilter()).subscribe({
      next: () => this.refresh(),
      error: (err) => this.fail(err),
    });
  }

  commit(): void {
    const session = this.session();
    if (!session || session.pending > 0 || !confirm('Commitar a sincronização? Nosso banco será atualizado.')) {
      return;
    }
    this.busy.set(true);
    this.syncService.commit(session.id).subscribe({
      next: (result) => {
        this.busy.set(false);
        this.result.set(result);
        this.session.set(null);
        this.view.set('done');
      },
      error: (err) => this.fail(err),
    });
  }

  binderListText(): string {
    return this.result()?.binder_list.join('\n') ?? '';
  }

  copyBinderList(): void {
    navigator.clipboard.writeText(this.binderListText()).then(() => this.copied.set(true));
  }

  downloadBinderList(): void {
    const blob = new Blob([this.binderListText()], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'lista-para-binder.txt';
    a.click();
    URL.revokeObjectURL(url);
  }

  newSync(): void {
    this.result.set(null);
    this.copied.set(false);
    this.selectedFile.set(null);
    this.view.set('landing');
  }

  colorLabel(color: string): string {
    return color === '__no_color__' ? 'Sem cor definida' : color;
  }
}
