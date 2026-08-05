export interface InventorySession {
  id: number;
  status: 'open' | 'completed' | 'discarded';
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  total_items: number;
  reviewed_count: number;
  pending_count: number;
  changed_count: number;
  new_count: number;
}
