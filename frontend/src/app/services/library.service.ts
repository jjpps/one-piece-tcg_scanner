import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LibraryCard } from '../interfaces/LibraryCard';
import { API_BASE_URL } from './api-url';

export const LIBRARY_PAGE_SIZE = 50;

export interface LibraryPage {
  items: LibraryCard[];
  total: number;
  page: number;
  page_size: number;
}

export interface LibraryQuery {
  color?: string;
  search?: string;
  searchBy?: string;
  page?: number;
  pageSize?: number;
}

@Injectable({
  providedIn: 'root',
})
export class LibraryService {
  private apiUrl = `${API_BASE_URL}/library`;
  constructor(private http: HttpClient) {}

  getLibrary(query: LibraryQuery = {}): Observable<LibraryPage> {
    let params = new HttpParams()
      .set('page', String(query.page ?? 1))
      .set('page_size', String(query.pageSize ?? LIBRARY_PAGE_SIZE));

    if (query.color) {
      params = params.set('color', query.color);
    }
    if (query.search) {
      params = params
        .set('search', query.search)
        .set('search_by', query.searchBy ?? 'code');
    }

    return this.http.get<LibraryPage>(this.apiUrl, { params });
  }
  getCardColors(): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/colors`);
  }
  getScanErrors(): Observable<LibraryCard[]> {
    return this.http.get<LibraryCard[]>(`${this.apiUrl}/errors`);
  }
  saveCardManually(fileName: string, code: string): Observable<any> {
    console.log(`Salvando carta com código ${code}`);
    return this.http.post(`${this.apiUrl}/errors/${fileName}`, { code: code });
  }
  addCardQuantity(code: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/addCard`, { code: code });
  }
  removeCardQuantity(code: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/removeCard/${code}`);
  }
}
