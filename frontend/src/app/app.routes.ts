import { Routes } from '@angular/router';
import { Home } from './pages/home/home';
import { ScanCards } from './pages/scan-cards/scan-cards';
import { Library } from './pages/library/library';
import { ScanErrors } from './pages/scan-errors/scan-errors';
import { CardsReview } from './pages/cards-review/cards-review';
import { DeckBuilding } from './pages/deck-building/deck-building';
import { DeckOutput } from './pages/deck-output/deck-output';
export const routes: Routes = [
  { path: '', component: Home },
  { path: 'home', component: Home },
  { path: 'scan-cards', component: ScanCards },
  { path: 'library', component: Library },
  { path: 'scan-errors', component: ScanErrors },
  { path: 'cards-review', component: CardsReview },
  { path: 'deck-building', component: DeckBuilding },
  { path: 'deck-output', component: DeckOutput },
];
