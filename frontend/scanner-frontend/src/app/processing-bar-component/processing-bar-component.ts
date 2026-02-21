import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ProcessingService } from './processing.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-processing-bar-component',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './processing-bar-component.html',
})
export class ProcessingBarComponent implements OnInit {

  total = 0;
  current = 0;
  processing = false;
  progress = 0;

  constructor(private processingService: ProcessingService,private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.processingService.status$
      .subscribe((res) => {
        this.total = res.total;
        this.current = res.current;
        this.processing = res.processing;

        this.progress = this.total > 0
          ? Math.round((this.current / this.total) * 100)
          : 0;
          console.log(this.progress)
          this.cdr.detectChanges();
      });
  }
}