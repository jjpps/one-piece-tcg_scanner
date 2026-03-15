import { HttpClient } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { LibraryCard } from "../interfaces/LibraryCard";
import { Observable } from "rxjs";

@Injectable({
  providedIn: 'root',
})
export class ReviewService {
  private apiUrl = 'http://localhost:5000/api/reviews';
  constructor(private http: HttpClient) {}
  getCardToReview(): Observable<LibraryCard[]>{
     return this.http.get<LibraryCard[]>(this.apiUrl);
  }
  approveCard(cardData:any): Observable<any> {    
    return this.http.post(`${this.apiUrl}/approve`, cardData );
  }
  reproveCard(cardData:any): Observable<any> {
    return this.http.post(`${this.apiUrl}/reprove`, cardData );
  }

}