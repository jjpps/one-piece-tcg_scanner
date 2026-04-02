import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeckOutput } from './deck-output';

describe('DeckOutput', () => {
  let component: DeckOutput;
  let fixture: ComponentFixture<DeckOutput>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeckOutput]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DeckOutput);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
