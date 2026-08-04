import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { Library } from './library';
import { LibraryService } from '../../services/library.service';

describe('Library', () => {
  let fixture: ComponentFixture<Library>;
  let component: Library;

  beforeEach(async () => {
    const libraryServiceSpy = jasmine.createSpyObj('LibraryService', [
      'getLibrary',
      'getCardColors',
      'addCardQuantity',
      'removeCardQuantity',
    ]);

    libraryServiceSpy.getLibrary.and.returnValue(of([
      { code: 'AAA', image_url: '', card_name: 'Alpha', quantity: 1, card_color: 'Blue' },
      { code: 'BBB', image_url: '', card_name: 'Beta', quantity: 1, card_color: 'Black' },
    ] as any));
    libraryServiceSpy.getCardColors.and.returnValue(of(['Blue', 'Black']));
    libraryServiceSpy.addCardQuantity.and.returnValue(of({}));
    libraryServiceSpy.removeCardQuantity.and.returnValue(of({}));

    await TestBed.configureTestingModule({
      imports: [Library],
      providers: [{ provide: LibraryService, useValue: libraryServiceSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(Library);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should filter cards by selected color', (done) => {
    component.onColorChange('Blue');

    component.libraryState$.subscribe((cards) => {
      expect(cards.map((card) => card.code)).toEqual(['AAA']);
      done();
    });
  });
});
