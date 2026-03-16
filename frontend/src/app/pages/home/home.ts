import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ReviewBadge } from '../review-badge/review-badge';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink,ReviewBadge],
  templateUrl: './home.html',
  styleUrl: './home.css',
})
export class Home {}
