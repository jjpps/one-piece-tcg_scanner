export interface ShoppingListItem {
  code: string;
  card_name: string;
  remaining: number;
}

export interface InvalidLine {
  raw: string;
  code: string | null;
  quantity: number;
  error?: string;
}

export interface ShoppingListImport {
  items: ShoppingListItem[];
  invalid: InvalidLine[];
}
