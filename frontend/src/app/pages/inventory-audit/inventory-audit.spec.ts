import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { InventoryAudit } from './inventory-audit';
import { InventoryService } from '../../services/inventory.service';
import { Router } from '@angular/router';

describe('InventoryAudit', () => {
  let fixture: ComponentFixture<InventoryAudit>;
  let component: InventoryAudit;
  let inventoryServiceSpy: {
    getCurrentSession: ReturnType<typeof vi.fn>;
    startSession: ReturnType<typeof vi.fn>;
    getColors: ReturnType<typeof vi.fn>;
    getItems: ReturnType<typeof vi.fn>;
    reviewItem: ReturnType<typeof vi.fn>;
    lookupCard: ReturnType<typeof vi.fn>;
    addNewCard: ReturnType<typeof vi.fn>;
    getDiff: ReturnType<typeof vi.fn>;
    applySession: ReturnType<typeof vi.fn>;
  };

  const openSession = {
    id: 1,
    status: 'open' as const,
    created_at: '',
    updated_at: '',
    completed_at: null,
    total_items: 10,
    reviewed_count: 2,
    pending_count: 8,
    changed_count: 1,
    new_count: 0,
  };

  const item = {
    code: 'OP01-001',
    card_name: 'Luffy',
    card_image_url: '',
    card_color: 'Red',
    system_quantity: 4,
    is_new_card: 0,
    reviewed: 0,
    changed: null,
    counted_quantity: null,
  };

  beforeEach(async () => {
    inventoryServiceSpy = {
      getCurrentSession: vi.fn().mockReturnValue(of({ session: null })),
      startSession: vi.fn().mockReturnValue(of({ session_id: 1, total_items: 10 })),
      getColors: vi.fn().mockReturnValue(of([{ card_color: 'Red', label: 'Red', total: 5, reviewed: 1, pending: 4 }])),
      getItems: vi.fn().mockReturnValue(of({ items: [item], total: 1, page: 1, page_size: 50 })),
      reviewItem: vi.fn().mockReturnValue(of({ ...item, reviewed: 1 })),
      lookupCard: vi.fn().mockReturnValue(of({})),
      addNewCard: vi.fn().mockReturnValue(of({})),
      getDiff: vi.fn().mockReturnValue(of({ updates: [], new_cards: [], pending_count: 0, pending_preview: [] })),
      applySession: vi.fn().mockReturnValue(of({ updated: 0, added: 0, left_pending: 0 })),
    };

    await TestBed.configureTestingModule({
      imports: [InventoryAudit],
      providers: [
        { provide: InventoryService, useValue: inventoryServiceSpy },
        { provide: Router, useValue: { navigate: vi.fn() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(InventoryAudit);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('shows the landing view with no active session on init', () => {
    expect(inventoryServiceSpy.getCurrentSession).toHaveBeenCalled();
    expect(component.view).toBe('landing');
    expect(component.session).toBeNull();
  });

  it('loads items for a color and switches to the review view', () => {
    component.session = { ...openSession };
    component.selectColor({ card_color: 'Red', label: 'Red', total: 5, reviewed: 1, pending: 4 });

    expect(component.view).toBe('review');
    expect(inventoryServiceSpy.getItems).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ color: 'Red', status: 'pending' })
    );
    expect(component.items.length).toBe(1);
  });

  it('marks a card as unchanged and removes it from the pending list', () => {
    component.session = { ...openSession };
    component.selectedColor = { card_color: 'Red', label: 'Red', total: 5, reviewed: 1, pending: 4 };
    component.items = [item];

    component.markUnchanged(item);

    expect(inventoryServiceSpy.reviewItem).toHaveBeenCalledWith(1, 'OP01-001', false);
    expect(component.items.length).toBe(0);
    expect(component.session.reviewed_count).toBe(3);
    expect(component.session.pending_count).toBe(7);
  });

  it('rejects an invalid counted quantity without calling reviewItem', () => {
    component.session = { ...openSession };
    component.selectedColor = { card_color: 'Red', label: 'Red', total: 5, reviewed: 1, pending: 4 };
    component.editingCode = item.code;
    component.editingQuantity = -1;

    component.confirmChangedQuantity(item);

    expect(inventoryServiceSpy.reviewItem).not.toHaveBeenCalled();
    expect(component.errorMessage).toContain('quantidade válida');
  });
});
