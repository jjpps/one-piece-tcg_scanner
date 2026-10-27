import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ShoppingListImport, ShoppingListItem } from '../interfaces/ShoppingListItem';
import { API_BASE_URL } from './api-url';

@Injectable({
  providedIn: 'root',
})
export class ShoppingListService {
  private apiUrl = `${API_BASE_URL}/shopping-list`;

  constructor(private http: HttpClient) {}

  list(): Observable<ShoppingListItem[]> {
    return this.http.get<ShoppingListItem[]>(this.apiUrl);
  }

  import(text: string): Observable<ShoppingListImport> {
    return this.http.post<ShoppingListImport>(`${this.apiUrl}/import`, { text });
  }

  addItem(code: string, quantity: number): Observable<ShoppingListItem> {
    return this.http.post<ShoppingListItem>(`${this.apiUrl}/items`, { code, quantity });
  }

  clear(): Observable<unknown> {
    return this.http.delete(this.apiUrl);
  }
}
