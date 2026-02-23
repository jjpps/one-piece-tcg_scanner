import { Routes } from '@angular/router';
import { HomeComponent } from './home/home.component';
import { ScanCardComponent } from './scan-card-component/scan-card-component';
import { LibraryComponent } from './library-component/library-component';
import { ScanErrors } from './scan-errors/scan-errors';

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
        path:'ScanErrors',
        component:ScanErrors
    },
    {
        path: '**',
        redirectTo: ''
    }
];
