import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MegaMenu } from './components/mega-menu/mega-menu';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, MegaMenu],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly title = signal('frontend');
}
