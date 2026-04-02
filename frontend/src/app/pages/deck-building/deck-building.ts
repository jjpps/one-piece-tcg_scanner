import { Component, inject } from '@angular/core';
import { NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DeckService } from '../../services/deck.service';
import { DeckCards } from '../../interfaces/DeckCards';
import { Router } from '@angular/router';

@Component({
  selector: 'app-deck-building',
  imports: [NgIf, FormsModule],
  templateUrl: './deck-building.html',
  styleUrl: './deck-building.css',
})
export class DeckBuilding {
  jsonText = '';
  jsonError: string | null = null;
  jsonResult: string | null = null;
  loading = false;

  private deckService = inject(DeckService);
  private router = inject(Router);

  onFormatJson(): void {
    this.jsonError = null;
    try {
      const parsed = JSON.parse(this.jsonText);
      this.jsonText = JSON.stringify(parsed, null, 2);
      this.jsonResult = 'JSON formatado com sucesso.';
    } catch (error: unknown) {
      this.jsonError = 'Erro ao formatar JSON: ' + (error instanceof Error ? error.message : String(error));
      this.jsonResult = null;
    }
  }

  async onSubmit(): Promise<void> {
    this.jsonError = null;
    this.jsonResult = null;

    if (!this.jsonText || !this.jsonText.trim()) {
      this.jsonError = 'Informe um JSON antes de enviar.';
      return;
    }

    let payload;
    try {
      payload = JSON.parse(this.jsonText);
    } catch (error: unknown) {
      this.jsonError = 'JSON inválido, corrija e tente novamente.';
      return;
    }

    this.loading = true;

    try {
      const response: any = await this.deckService.uploadDeck(payload).toPromise();
      if(response && response.cards && response.cards.length > 0) {
        this.jsonResult = `Deck enviado com sucesso! ${response.cards.length} cartas processadas.`;
        // Navegar para deck-output com os dados
        this.router.navigate(['/deck-output'], { state: { response } });
      }     
      this.loading = false;
    } catch (error: unknown) {
      this.jsonError = 'Falha no envio do deck: ' + (error instanceof Error ? error.message : String(error));
    } finally {
      this.loading = false;
    }
  }
}
