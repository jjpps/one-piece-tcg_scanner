import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { DeckMenu } from '../../components/deck-menu/deck-menu';
import { InvalidLine, ShoppingListItem } from '../../interfaces/ShoppingListItem';
import { ShoppingListService } from '../../services/shopping-list.service';

@Component({
  selector: 'app-shopping-list',
  imports: [FormsModule, DeckMenu],
  templateUrl: './shopping-list.html',
})
export class ShoppingList implements OnInit {
  listText = '';
  items = signal<ShoppingListItem[]>([]);
  invalid = signal<InvalidLine[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);

  private service = inject(ShoppingListService);

  async ngOnInit(): Promise<void> {
    this.items.set(await firstValueFrom(this.service.list()));
  }

  async onImport(): Promise<void> {
    this.error.set(null);
    this.loading.set(true);
    try {
      const result = await firstValueFrom(this.service.import(this.listText));
      this.items.set(result.items);
      this.invalid.set(result.invalid);
      this.listText = '';
    } catch (e: any) {
      this.error.set(e?.error?.error ?? 'Falha ao importar a lista.');
    } finally {
      this.loading.set(false);
    }
  }

  async addInvalid(line: InvalidLine): Promise<void> {
    line.error = undefined;
    try {
      await firstValueFrom(this.service.addItem(line.code ?? '', line.quantity));
      this.invalid.update((l) => l.filter((x) => x !== line));
      this.items.set(await firstValueFrom(this.service.list()));
    } catch (e: any) {
      line.error = e?.error?.error ?? 'Falha ao adicionar.';
      this.invalid.update((l) => [...l]);
    }
  }

  copyList(): void {
    const list = this.items().map((i) => `${i.remaining} ${i.card_name} (${i.code})`).join('\n');
    navigator.clipboard.writeText(list).then(
      () => alert('Lista copiada para a área de transferência!'),
      (err) => console.error('Erro ao copiar: ', err),
    );
  }

  async clear(): Promise<void> {
    if (!confirm('Limpar a lista de compras?')) return;
    await firstValueFrom(this.service.clear());
    this.items.set([]);
    this.invalid.set([]);
  }
}
