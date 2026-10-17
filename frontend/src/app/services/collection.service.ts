import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Collection } from '../interfaces/Collection';
import { API_BASE_URL } from './api-url';

@Injectable({
  providedIn: 'root',
})
export class CollectionService {
  constructor(private http: HttpClient) {}

  list(): Observable<Collection[]> {
    return this.http.get<Collection[]>(`${API_BASE_URL}/collections`);
  }
}
