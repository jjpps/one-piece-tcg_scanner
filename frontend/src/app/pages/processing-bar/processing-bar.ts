import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { ProcessingService } from '../../services/processing.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-processing-bar',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './processing-bar.html',
  styleUrl: './processing-bar.css',
})
export class ProcessingBar {
    status$!: Observable<any>;

  constructor(private processingService: ProcessingService) {
    this.status$ = this.processingService.status$;
  }
}
