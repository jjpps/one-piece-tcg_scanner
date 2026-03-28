import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, interval, Observable, Subscription } from 'rxjs';
import { LibraryCard } from '../interfaces/LibraryCard';

@Injectable({
  providedIn: 'root',
})
export class LibraryService {
  private apiUrl = 'http://localhost:5000/api/library';
  constructor(private http: HttpClient) {}
  getLibrary(): Observable<LibraryCard[]> {
    return this.http.get<LibraryCard[]>(this.apiUrl);
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
