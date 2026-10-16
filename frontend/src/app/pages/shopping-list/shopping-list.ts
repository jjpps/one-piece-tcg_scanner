import { Component, inject, OnInit } from '@angular/core';
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
  items: ShoppingListItem[] = [];
  invalid: InvalidLine[] = [];
  loading = false;
  error: string | null = null;

  private service = inject(ShoppingListService);

  async ngOnInit(): Promise<void> {
    this.items = await firstValueFrom(this.service.list());
  }

  async onImport(): Promise<void> {
    this.error = null;
    this.loading = true;
    try {
      const result = await firstValueFrom(this.service.import(this.listText));
      this.items = result.items;
      this.invalid = result.invalid;
      this.listText = '';
    } catch (e: any) {
      this.error = e?.error?.error ?? 'Falha ao importar a lista.';
    } finally {
      this.loading = false;
    }
  }

  async addInvalid(line: InvalidLine): Promise<void> {
    line.error = undefined;
    try {
      await firstValueFrom(this.service.addItem(line.code ?? '', line.quantity));
      this.invalid = this.invalid.filter((l) => l !== line);
      this.items = await firstValueFrom(this.service.list());
    } catch (e: any) {
      line.error = e?.error?.error ?? 'Falha ao adicionar.';
    }
  }

  copyList(): void {
    const list = this.items.map((i) => `${i.remaining} ${i.card_name} (${i.code})`).join('\n');
    navigator.clipboard.writeText(list).then(
      () => alert('Lista copiada para a área de transferência!'),
      (err) => console.error('Erro ao copiar: ', err),
    );
  }

  async clear(): Promise<void> {
    if (!confirm('Limpar a lista de compras?')) return;
    await firstValueFrom(this.service.clear());
    this.items = [];
    this.invalid = [];
  }
}
