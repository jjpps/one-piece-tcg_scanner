import { Routes } from '@angular/router';
import { HomeComponent } from './home/home.component';
import { ScanCardComponent } from './scan-card-component/scan-card-component';

export const routes: Routes = [
    {
        path: '',
        component: HomeComponent
    },
    {
        path: 'ScanCards',
        component: ScanCardComponent
    },
    {
        path: '**',
        redirectTo: ''
    }
];
