import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeckBuilding } from './deck-building';

describe('DeckBuilding', () => {
  let component: DeckBuilding;
  let fixture: ComponentFixture<DeckBuilding>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeckBuilding]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DeckBuilding);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
