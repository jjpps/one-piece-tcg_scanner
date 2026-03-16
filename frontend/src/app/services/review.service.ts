import { HttpClient } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { BehaviorSubject, Observable } from "rxjs";
import { LibraryCard } from "../interfaces/LibraryCard";

@Injectable({
  providedIn: 'root',
})
export class ReviewService {
  private apiUrl = 'http://localhost:5000/api/reviews';
  private cardsSubject = new BehaviorSubject<LibraryCard[]>([]);
  public cards$ = this.cardsSubject.asObservable();

  constructor(private http: HttpClient) {}

  loadCards(): void {
    this.http.get<LibraryCard[]>(this.apiUrl).subscribe({
      next: (cards) => this.cardsSubject.next(cards),
      error: () => this.cardsSubject.next([])
    });
  }

  getCardToReview(): Observable<LibraryCard[]> {
    return this.cards$;
  }

  approveCard(cardData: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/approve`, cardData);
  }

  reproveCard(cardData: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/reprove`, cardData);
  }
}