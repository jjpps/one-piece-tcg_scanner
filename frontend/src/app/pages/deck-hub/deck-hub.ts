import { Component } from '@angular/core';
import { DeckMenu } from '../../components/deck-menu/deck-menu';

@Component({
  selector: 'app-deck-hub',
  imports: [DeckMenu],
  template: `<app-deck-menu />`,
})
export class DeckHub {}
