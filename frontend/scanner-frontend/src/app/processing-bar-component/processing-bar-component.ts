import { Component, OnDestroy, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-processing-bar-component',
  standalone: true,
  templateUrl: './processing-bar-component.html',
  styleUrl: './processing-bar-component.css',
})
export class ProcessingBarComponent implements OnInit, OnDestroy {

  total = 0;
  current = 0;
  processing = false;
  progress = 0;

  private statusUrl =  'http://localhost:5000/api/status'; // use proxy se configurado
  private pollingSub?: Subscription;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.startPolling();
  }

  startPolling(): void {
    this.pollingSub = interval(1000).subscribe(() => {
      this.http.get<any>(this.statusUrl)
        .subscribe((res) => {

          this.total = res.total;
          this.current = res.current;
          this.processing = res.processing;

          this.progress = this.total > 0
            ? Math.round((this.current / this.total) * 100)
            : 0;

          // para polling quando finalizar
          // if (!this.processing) {
          //   this.stopPolling();
          // }
        });
    });
  }

  stopPolling(): void {
    this.pollingSub?.unsubscribe();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }
}