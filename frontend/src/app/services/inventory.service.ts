import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from './api-url';
import { InventorySession } from '../interfaces/InventorySession';
import { InventoryColor } from '../interfaces/InventoryColor';
import { InventorySessionItem } from '../interfaces/InventorySessionItem';
import { InventoryDiff } from '../interfaces/InventoryDiff';

export interface InventoryItemsPage {
  items: InventorySessionItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface InventoryItemsQuery {
  color?: string;
  status?: 'pending' | 'reviewed' | 'all';
  search?: string;
  page?: number;
  pageSize?: number;
}

@Injectable({
  providedIn: 'root',
})
export class InventoryService {
  private apiUrl = `${API_BASE_URL}/inventory`;
  constructor(private http: HttpClient) {}

  getCurrentSession(): Observable<{ session: InventorySession | null }> {
    return this.http.get<{ session: InventorySession | null }>(`${this.apiUrl}/session`);
  }

  startSession(): Observable<{ session_id: number; total_items: number }> {
    return this.http.post<{ session_id: number; total_items: number }>(`${this.apiUrl}/session`, {});
  }

  getColors(sessionId: number): Observable<InventoryColor[]> {
    return this.http.get<InventoryColor[]>(`${this.apiUrl}/session/${sessionId}/colors`);
  }

  getItems(sessionId: number, query: InventoryItemsQuery): Observable<InventoryItemsPage> {
    let params = new HttpParams();
    if (query.color) {
      params = params.set('color', query.color);
    }
    params = params.set('status', query.status ?? 'pending');
    if (query.search) {
      params = params.set('search', query.search);
    }
    params = params.set('page', String(query.page ?? 1));
    params = params.set('page_size', String(query.pageSize ?? 50));

    return this.http.get<InventoryItemsPage>(`${this.apiUrl}/session/${sessionId}/items`, { params });
  }

  reviewItem(sessionId: number, code: string, changed: boolean, countedQuantity?: number): Observable<InventorySessionItem> {
    return this.http.patch<InventorySessionItem>(`${this.apiUrl}/session/${sessionId}/items/${code}`, {
      changed,
      counted_quantity: countedQuantity,
    });
  }

  lookupCard(code: string): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/lookup/${code}`);
  }

  addNewCard(sessionId: number, code: string, countedQuantity: number): Observable<InventorySessionItem> {
    return this.http.post<InventorySessionItem>(`${this.apiUrl}/session/${sessionId}/items`, {
      code,
      counted_quantity: countedQuantity,
    });
  }

  getDiff(sessionId: number): Observable<InventoryDiff> {
    return this.http.get<InventoryDiff>(`${this.apiUrl}/session/${sessionId}/diff`);
  }

  applySession(sessionId: number): Observable<{ updated: number; added: number; left_pending: number }> {
    return this.http.post<{ updated: number; added: number; left_pending: number }>(`${this.apiUrl}/session/${sessionId}/apply`, {});
  }
}
