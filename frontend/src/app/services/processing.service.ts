import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, interval, Subscription } from 'rxjs';
import { API_BASE_URL } from './api-url';

@Injectable({
  providedIn: 'root'
})
export class ProcessingService {

  private statusUrl = `${API_BASE_URL}/status`;

  private pollingSub?: Subscription;

  private statusSubject = new BehaviorSubject<any>({
    total: 0,
    current: 0,
    processing: false
  });

  status$ = this.statusSubject.asObservable();

  constructor(private http: HttpClient) {}

  startPolling() {

    if (this.pollingSub) return; // evita múltiplos intervalos

    this.pollingSub = interval(1000).subscribe(() => {
      this.http.get<any>(this.statusUrl)
        .subscribe((res) => {

          this.statusSubject.next(res);

          if (!res.processing) {
            this.stopPolling();
          }
        });
    });
  }

  stopPolling() {
    this.pollingSub?.unsubscribe();
    this.pollingSub = undefined;
  }
}