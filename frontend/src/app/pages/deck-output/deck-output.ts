import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgFor, NgClass, NgIf } from '@angular/common';

interface Card {
  card_name: string;
  code: string;
  image_url: string;
  quantityOwned: number;
  quantityRequired: number;
}

interface DeckResponse {
  cards: Card[];
  deckName: string;
}

@Component({
  selector: 'app-deck-output',
  imports: [NgFor, NgClass, NgIf],
  templateUrl: './deck-output.html',
  styleUrl: './deck-output.css',
})
export class DeckOutput implements OnInit {
  deckName: string = '';
  cards: Card[] = [];
  viewMode: 'card' | 'list' = 'list';

  constructor(private route: ActivatedRoute) {}

  ngOnInit(): void {
    const state = history.state as { response?: DeckResponse };
    if (state.response) {
      this.deckName = state.response.deckName;
      this.cards = state.response.cards;
    }
  }

  get totalMissing(): number {
    return this.cards.reduce((total, card) => {
      if (card.quantityOwned < card.quantityRequired) {
        return total + (card.quantityRequired - card.quantityOwned);
      }
      return total;
    }, 0);
  }

  toggleView(): void {
    this.viewMode = this.viewMode === 'card' ? 'list' : 'card';
  }

  copyList(): void {
    const list = this.cards.filter(card => card.quantityOwned < card.quantityRequired).map(card => `${card.quantityRequired - card.quantityOwned} ${card.card_name} (${card.code})`).join('\n');
    navigator.clipboard.writeText(list).then(() => {
      alert('Lista copiada para a área de transferência!');
    }).catch(err => {
      console.error('Erro ao copiar: ', err);
    });
  }
}
