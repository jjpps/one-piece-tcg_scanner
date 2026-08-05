export interface InventorySessionItem {
  code: string;
  card_name: string;
  card_image_url: string;
  card_color: string | null;
  system_quantity: number;
  is_new_card: number;
  reviewed: number;
  changed: number | null;
  counted_quantity: number | null;
}
