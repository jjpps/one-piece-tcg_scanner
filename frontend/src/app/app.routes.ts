import { Routes } from '@angular/router';
import { ScanCards } from './pages/scan-cards/scan-cards';
import { Library } from './pages/library/library';
import { ScanErrors } from './pages/scan-errors/scan-errors';
import { CardsReview } from './pages/cards-review/cards-review';
import { DeckBuilding } from './pages/deck-building/deck-building';
import { DeckOutput } from './pages/deck-output/deck-output';
import { InventoryAudit } from './pages/inventory-audit/inventory-audit';
import { ShoppingList } from './pages/shopping-list/shopping-list';
export const routes: Routes = [
  { path: '', pathMatch: 'full', children: [] },
  { path: 'home', redirectTo: '', pathMatch: 'full' },
  { path: 'scan-cards', component: ScanCards },
  { path: 'library', component: Library },
  { path: 'scan-errors', component: ScanErrors },
  { path: 'cards-review', component: CardsReview },
  { path: 'shopping-list', component: ShoppingList },
  { path: 'deck-building', component: DeckBuilding },
  { path: 'deck-output', component: DeckOutput },
  { path: 'inventory-audit', component: InventoryAudit },
];
