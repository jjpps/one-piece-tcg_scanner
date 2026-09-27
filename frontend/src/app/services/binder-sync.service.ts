import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from './api-url';

export type SyncResolution = 'binder' | 'ours' | 'ignore';
export type SyncKind = 'binder_only' | 'ours_only' | 'both';

export interface SyncSession {
  id: number;
  status: string;
  created_at: string;
  total: number;
  pending: number;
  binder_only: number;
  ours_only: number;
  both: number;
  colors: { card_color: string; total: number; pending: number }[];
}

export interface SyncItem {
  code: string;
  card_name: string | null;
  card_image_url: string | null;
  card_color: string | null;
  our_quantity: number;
  binder_quantity: number;
  resolution: SyncResolution | null;
  kind: SyncKind;
}

export interface SyncItemsQuery {
  kind?: SyncKind | '';
  color?: string;
  status?: 'pending' | 'resolved' | '';
  search?: string;
  page?: number;
  pageSize?: number;
}

export interface SyncCommitResult {
  updated: number;
  added: number;
  failed: string[];
  binder_list: string[];
}

@Injectable({
  providedIn: 'root',
})
export class BinderSyncService {
  private apiUrl = `${API_BASE_URL}/sync`;
  constructor(private http: HttpClient) {}

  getCurrentSession(): Observable<{ session: SyncSession | null }> {
    return this.http.get<{ session: SyncSession | null }>(`${this.apiUrl}/session`);
  }

  importCsv(file: File): Observable<{ session_id: number; total_divergences: number }> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<{ session_id: number; total_divergences: number }>(`${this.apiUrl}/session`, form);
  }

  discard(sessionId: number): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/session/${sessionId}/discard`, {});
  }

  getItems(sessionId: number, query: SyncItemsQuery): Observable<{ items: SyncItem[]; total: number }> {
    let params = new HttpParams()
      .set('page', String(query.page ?? 1))
      .set('page_size', String(query.pageSize ?? 50));
    if (query.kind) params = params.set('kind', query.kind);
    if (query.color) params = params.set('color', query.color);
    if (query.status) params = params.set('status', query.status);
    if (query.search) params = params.set('search', query.search);
    return this.http.get<{ items: SyncItem[]; total: number }>(`${this.apiUrl}/session/${sessionId}/items`, { params });
  }

  resolveItem(sessionId: number, code: string, resolution: SyncResolution | null): Observable<SyncItem> {
    return this.http.patch<SyncItem>(`${this.apiUrl}/session/${sessionId}/items/${code}`, { resolution });
  }

  resolveBulk(sessionId: number, resolution: SyncResolution, kind?: SyncKind | '', color?: string): Observable<{ updated: number }> {
    return this.http.post<{ updated: number }>(`${this.apiUrl}/session/${sessionId}/resolve`, {
      resolution,
      kind: kind || null,
      color: color || null,
    });
  }

  commit(sessionId: number): Observable<SyncCommitResult> {
    return this.http.post<SyncCommitResult>(`${this.apiUrl}/session/${sessionId}/commit`, {});
  }
}
