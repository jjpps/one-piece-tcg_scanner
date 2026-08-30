import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { Library } from './library';
import { LibraryService } from '../../services/library.service';

describe('Library', () => {
  let fixture: ComponentFixture<Library>;
  let component: Library;
  let getLibrary: any;

  beforeEach(async () => {
    getLibrary = vi.fn().mockReturnValue(
      of({
        items: [{ code: 'AAA', image_url: '', card_name: 'Alpha', quantity: 1, card_color: 'Blue' }],
        total: 120,
        page: 1,
        page_size: 50,
      } as any)
    );

    const libraryServiceSpy = {
      getLibrary,
      getCardColors: vi.fn().mockReturnValue(of(['Blue', 'Black'])),
      addCardQuantity: vi.fn().mockReturnValue(of({})),
      removeCardQuantity: vi.fn().mockReturnValue(of({})),
    };

    await TestBed.configureTestingModule({
      imports: [Library],
      providers: [{ provide: LibraryService, useValue: libraryServiceSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(Library);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('repassa o filtro de cor para o backend', () => {
    component.onColorChange('Blue');
    fixture.detectChanges();

    expect(getLibrary).toHaveBeenLastCalledWith(expect.objectContaining({ color: 'Blue' }));
  });

  it('volta para a página 1 ao aplicar um filtro', () => {
    component.nextPage();
    component.nextPage();
    fixture.detectChanges();
    expect(component.page).toBe(3);

    component.searchTerm = 'luffy';
    component.search();
    fixture.detectChanges();

    expect(component.page).toBe(1);
    expect(getLibrary).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 1, search: 'luffy' })
    );
  });

  it('não avança além da última página', () => {
    // total 120, pageSize 50 => 3 páginas
    component.nextPage();
    component.nextPage();
    component.nextPage();

    expect(component.page).toBe(3);
    expect(component.hasNextPage).toBe(false);
  });
});
