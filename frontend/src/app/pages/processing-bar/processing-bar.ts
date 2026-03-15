import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Output, OnInit, OnDestroy } from '@angular/core';
import { ProcessingService } from '../../services/processing.service';
import { Observable, Subscription } from 'rxjs';

@Component({
  selector: 'app-processing-bar',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './processing-bar.html',
  styleUrl: './processing-bar.css',
})
export class ProcessingBar {
    status$!: Observable<any>;

  // emit when processing finishes (transition from true to false)
  @Output() processingComplete = new EventEmitter<void>();

  private lastProcessing = false;
  private statusSubscription?: Subscription;

  constructor(private processingService: ProcessingService) {
    this.status$ = this.processingService.status$;
  }

  ngOnInit(): void {
    // watch the observable and fire once when processing becomes false
    this.statusSubscription = this.status$.subscribe(status => {
      if (this.lastProcessing && !status.processing) {
        this.processingComplete.emit();
      }
      this.lastProcessing = status.processing;
    });
  }

  ngOnDestroy(): void {
    this.statusSubscription?.unsubscribe();
  }
}
