import { Injectable } from "@angular/core";
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { DeckCards } from "../interfaces/DeckCards";

@Injectable({
  providedIn: 'root',
})
export class DeckService {
    private apiUrl = 'http://localhost:5000/api/upload/deck';

    constructor(private http: HttpClient) {}

    uploadDeck(deckData: any): Observable<DeckCards[]> {
        return this.http.post<DeckCards[]>(this.apiUrl, deckData);
    }
}