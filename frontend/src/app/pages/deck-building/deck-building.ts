import { Component, inject } from '@angular/core';
import { NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DeckService } from '../../services/deck.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-deck-building',
  imports: [NgIf, FormsModule],
  templateUrl: './deck-building.html',
  styleUrl: './deck-building.css',
})
export class DeckBuilding {
  listText = '';
  jsonError: string | null = null;
  jsonResult: string | null = null;
  loading = false;

  private deckService = inject(DeckService);
  private router = inject(Router);

  async onSubmit(): Promise<void> {
    this.jsonError = null;
    this.jsonResult = null;

    if (!this.listText || !this.listText.trim()) {
      this.jsonError = 'Informe a lista de cartas antes de enviar.';
      return;
    }

    this.loading = true;

    try {
      const lines = this.listText
        .split(/\n|\r\n/)
        .map((line) => line.trim())
        .filter(Boolean);

      const payload = {
        deckName: 'Deck',
        cards: lines,
      };

      const response: any = await this.deckService.uploadDeck(payload).toPromise();
      if (response && response.cards && response.cards.length > 0) {
        this.jsonResult = `Deck enviado com sucesso! ${response.cards.length} cartas processadas.`;
        this.router.navigate(['/deck-output'], { state: { response } });
      } else {
        this.jsonError = 'Nenhuma carta válida foi encontrada para processar.';
      }
    } catch (error: unknown) {
      this.jsonError = 'Falha no envio do deck: ' + (error instanceof Error ? error.message : String(error));
    } finally {
      this.loading = false;
    }
  }
}
