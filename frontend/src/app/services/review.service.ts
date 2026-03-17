import { HttpClient } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { BehaviorSubject, Observable } from "rxjs";
import { LibraryCard } from "../interfaces/LibraryCard";
import { LocalCard } from "../interfaces/LocalCard";

@Injectable({
  providedIn: 'root',
})
export class ReviewService {
  private apiUrl = 'http://localhost:5000/api/reviews';
  private cardsSubject = new BehaviorSubject<LocalCard[]>([]);
  public cards$ = this.cardsSubject.asObservable();

  constructor(private http: HttpClient) {}

  loadCards(): void {
    this.http.get<LocalCard[]>(this.apiUrl).subscribe({
      next: (cards) => this.cardsSubject.next(cards),
      error: () => this.cardsSubject.next([])
    });
  }

  getCardToReview(): Observable<LocalCard[]> {
    return this.cards$;
  }

  approveCard(cardData: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/approve`, cardData);
  }

  reproveCard(cardData: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/reprove`, cardData);
  }
}