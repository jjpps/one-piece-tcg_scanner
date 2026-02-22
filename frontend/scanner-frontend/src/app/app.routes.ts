import { Routes } from '@angular/router';
import { HomeComponent } from './home/home.component';
import { ScanCardComponent } from './scan-card-component/scan-card-component';
import { LibraryComponent } from './library-component/library-component';

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
        path: 'Library',
        component: LibraryComponent
    },
    {
        path: '**',
        redirectTo: ''
    }
];
