import { Routes } from '@angular/router';
import { Home } from './pages/home/home';
import { ScanCards } from './pages/scan-cards/scan-cards';
import { Library } from './pages/library/library';
import { ScanErrors } from './pages/scan-errors/scan-errors';
export const routes: Routes = [
  {
    path: '',
    component: Home,
  },
  { path: 'scan-cards', component: ScanCards },
  { path: 'library', component: Library },
  { path: 'scan-errors', component: ScanErrors },
];
