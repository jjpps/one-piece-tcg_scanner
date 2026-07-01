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

  function createMouseEvent(clientX: number, clientY: number, width = 200, height = 120): MouseEvent {
    const image = document.createElement('img') as any;
    image.getBoundingClientRect = () => ({
      left: 0,
      top: 0,
      width,
      height,
      right: width,
      bottom: height,
      x: 0,
      y: 0,
      toJSON: () => ({})
    } as DOMRect);

    return {
      currentTarget: image,
      clientX,
      clientY,
    } as unknown as MouseEvent;
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should activate zoom on image enter for the hovered card', () => {
    const imageUrl = 'https://example.com/card.jpg';
    const event = createMouseEvent(100, 60);

    component.onImageMouseEnter(imageUrl, 'card-1', event);

    expect(component.zoomActive).toBeTrue();
    expect(component.activeZoomCardId).toBe('card-1');
    expect(component.zoomImageSrc).toBe(imageUrl);
    expect(component.zoomStyle['background-image']).toContain(imageUrl);
    expect(component.zoomStyle['background-position']).toBe('50% 50%');
  });

  it('should update zoom style on mouse move when active', () => {
    const imageUrl = 'https://example.com/card.jpg';
    component.zoomActive = true;
    component.activeZoomCardId = 'card-1';
    component.zoomImageSrc = imageUrl;

    component.onImageMouseMove(createMouseEvent(160, 90));

    expect(component.zoomStyle['background-position']).toBe('80% 75%');
    expect(component.zoomStyle['background-image']).toContain(imageUrl);
  });

  it('should deactivate zoom on image leave', () => {
    component.zoomActive = true;
    component.zoomImageSrc = 'https://example.com/card.jpg';

    component.onImageMouseLeave();

    expect(component.zoomActive).toBeFalse();
    expect(component.zoomImageSrc).toBeNull();
    expect(component.zoomStyle).toEqual({});
  });

  it('should render zoom preview when active', () => {
    component.zoomActive = true;
    component.zoomImageSrc = 'https://example.com/card.jpg';
    component.zoomStyle = {
      'background-image': 'url(https://example.com/card.jpg)',
      'background-position': '50% 50%',
      'background-size': '400px 240px',
    };

    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('.zoom-preview')).toBeTruthy();
  });
});
