import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { Library } from './library';
import { LibraryService } from '../../services/library.service';

describe('Library', () => {
  let fixture: ComponentFixture<Library>;
  let component: Library;

  beforeEach(async () => {
    const libraryServiceSpy = {
      getLibrary: vi.fn().mockReturnValue(of([
        { code: 'AAA', image_url: '', card_name: 'Alpha', quantity: 1, card_color: 'Blue' },
        { code: 'BBB', image_url: '', card_name: 'Beta', quantity: 1, card_color: 'Black' },
      ] as any)),
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

  it('should filter cards by selected color', () => {
    component.onColorChange('Blue');

    let result: any[] = [];
    component.libraryState$.subscribe((cards) => {
      result = cards;
    });

    expect(result.map((card) => card.code)).toEqual(['AAA']);
  });
});
