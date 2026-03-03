import { HttpClient } from '@angular/common/http';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProcessingService } from '../../services/processing.service';
import { ProcessingBar } from '../processing-bar/processing-bar';
@Component({
  selector: 'app-scan-cards',
  imports: [FormsModule,ProcessingBar],
  templateUrl: './scan-cards.html',
  styleUrl: './scan-cards.css',
})
export class ScanCards {
selectedFiles: File[] = [];
  loading = false;

  private apiUrl = 'http://localhost:5000/api/upload';

  constructor(
    private http: HttpClient,
    private processingService: ProcessingService
  ) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;

    if (!input.files || input.files.length === 0) return;

    this.selectedFiles = Array.from(input.files);
    console.log('Arquivos selecionados:', this.selectedFiles);
  }

  onSubmit(): void {
    if (!this.selectedFiles.length) return;

    const formData = new FormData();

    this.selectedFiles.forEach((file) => {
      formData.append('images', file);
    });

    this.loading = true;
    console.log('Enviando arquivos para:', this.apiUrl);

    this.http.post(this.apiUrl, formData).subscribe({
      next: (response) => {
        console.log('Upload sucesso:', response);
        this.loading = false;
        this.selectedFiles = [];        
        this.processingService.startPolling();
      },
      error: (error) => {
        console.error('Erro no upload:', error);
        this.loading = false;
        alert('Ocorreu um erro ao enviar os arquivos. Por favor, tente novamente.');
      },
    });
  }
}
