import { Routes } from '@angular/router';
import { Home } from './pages/home/home';
import { ScanCards } from './pages/scan-cards/scan-cards';
export const routes: Routes = [
  {
    path: '',
    component: Home,
  },
  { path: 'scan-cards', component: ScanCards },
];
