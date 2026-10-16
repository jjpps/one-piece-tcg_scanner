import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-deck-menu',
  imports: [RouterLink],
  template: `
    <nav class="navbar bg-body-tertiary border-bottom px-3">
      <a routerLink="/home" class="btn btn-outline-secondary btn-sm">Home</a>
      <div class="position-relative">
        <button type="button" class="btn btn-outline-dark" (click)="open = !open">Deck ▾</button>
        @if (open) {
          <div class="list-group position-absolute end-0 mt-1 shadow" style="min-width: 200px; z-index: 10">
            <a routerLink="/deck-building" class="list-group-item list-group-item-action">Deck Building</a>
            <a routerLink="/shopping-list" class="list-group-item list-group-item-action">Lista de Compras</a>
          </div>
        }
      </div>
    </nav>
  `,
})
export class DeckMenu {
  open = false;
}
