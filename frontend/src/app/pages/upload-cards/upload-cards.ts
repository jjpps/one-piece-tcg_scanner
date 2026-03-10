import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ProcessingService } from '../../services/processing.service';
import { FormsModule } from '@angular/forms';
@Component({
  selector: 'app-upload-cards',
  imports: [FormsModule],
  templateUrl: './upload-cards.html',
  styleUrl: './upload-cards.css',
})
export class UploadCards {
  selectedFiles: File[] = [];
  loading = false;
  private apiUrl = 'http://localhost:5000/api/upload';
  constructor(private http: HttpClient,
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
        this.selectedFiles = [];      
        alert('Ocorreu um erro ao enviar os arquivos. Por favor, tente novamente.');
      },
    });
  }
}
