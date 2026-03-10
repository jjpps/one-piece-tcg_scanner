import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UploadCards } from './upload-cards';

describe('UploadCards', () => {
  let component: UploadCards;
  let fixture: ComponentFixture<UploadCards>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadCards]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UploadCards);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
