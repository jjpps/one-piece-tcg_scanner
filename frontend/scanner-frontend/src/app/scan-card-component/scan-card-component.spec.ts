import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScanCardComponent } from './scan-card-component';

describe('ScanCardComponent', () => {
  let component: ScanCardComponent;
  let fixture: ComponentFixture<ScanCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScanCardComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ScanCardComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
