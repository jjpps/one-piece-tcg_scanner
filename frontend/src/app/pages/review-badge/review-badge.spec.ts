import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ReviewBadge } from './review-badge';

describe('ReviewBadge', () => {
  let component: ReviewBadge;
  let fixture: ComponentFixture<ReviewBadge>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReviewBadge]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ReviewBadge);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
