import { Injectable } from "@angular/core";
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { DeckCards } from "../interfaces/DeckCards";
import { API_BASE_URL } from './api-url';

@Injectable({
  providedIn: 'root',
})
export class DeckService {
    private apiUrl = `${API_BASE_URL}/upload/deck`;

    constructor(private http: HttpClient) {}

    uploadDeck(deckData: any): Observable<DeckCards[]> {
        return this.http.post<DeckCards[]>(this.apiUrl, deckData);
    }
}