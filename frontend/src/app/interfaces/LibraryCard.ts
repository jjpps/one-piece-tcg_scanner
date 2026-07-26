export interface LibraryCard {
  id: string;
  code: string;
  image_url: string;
  card_name: string;
  quantity: number;
  card_color?: string | null;
}