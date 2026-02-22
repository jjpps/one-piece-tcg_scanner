import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ProcessingBarComponent } from './processing-bar-component';

describe('ProcessingBarComponent', () => {
  let component: ProcessingBarComponent;
  let fixture: ComponentFixture<ProcessingBarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProcessingBarComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProcessingBarComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
