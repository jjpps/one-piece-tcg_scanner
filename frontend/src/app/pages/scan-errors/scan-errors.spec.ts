import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScanErrors } from './scan-errors';

describe('ScanErrors', () => {
  let component: ScanErrors;
  let fixture: ComponentFixture<ScanErrors>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScanErrors]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ScanErrors);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
