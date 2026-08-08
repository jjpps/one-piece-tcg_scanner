export interface InventoryDiffUpdate {
  code: string;
  card_name: string;
  system_quantity: number;
  counted_quantity: number;
}

export interface InventoryDiffNewCard {
  code: string;
  card_name: string;
  counted_quantity: number;
}

export interface InventoryDiffPendingItem {
  code: string;
  card_name: string;
  card_color: string | null;
}

export interface InventoryDiff {
  updates: InventoryDiffUpdate[];
  new_cards: InventoryDiffNewCard[];
  pending_count: number;
  pending_preview: InventoryDiffPendingItem[];
}
