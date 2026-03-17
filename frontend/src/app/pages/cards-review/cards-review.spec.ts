import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CardsReview } from './cards-review';

describe('CardsReview', () => {
  let component: CardsReview;
  let fixture: ComponentFixture<CardsReview>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CardsReview]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CardsReview);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
