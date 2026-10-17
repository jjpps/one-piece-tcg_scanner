import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';
import { Collection } from '../../interfaces/Collection';
import { CollectionService } from '../../services/collection.service';

const TYPE_ORDER = ['OP', 'EB', 'ST'];
const RADIUS = 52;
export const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function percent(c: Collection): number {
  return c.total ? Math.round((c.owned / c.total) * 100) : 0;
}

// Mais nova primeiro: tipo (OP, EB, ST) e depois número decrescente.
export function byNewest(a: Collection, b: Collection): number {
  const type = (c: Collection) => TYPE_ORDER.indexOf(c.prefix.slice(0, 2));
  return type(a) - type(b) || b.prefix.localeCompare(a.prefix);
}

@Component({
  selector: 'app-collection-tracker',
  imports: [RouterLink],
  templateUrl: './collection-tracker.html',
  styleUrl: './collection-tracker.css',
})
export class CollectionTracker {
  readonly circumference = CIRCUMFERENCE;
  readonly radius = RADIUS;
  readonly percent = percent;

  private collections = toSignal(
    inject(CollectionService).list().pipe(catchError(() => of(null))),
    { initialValue: [] as Collection[] | null },
  );
  failed = computed(() => this.collections() === null);
  sorted = computed(() => [...(this.collections() ?? [])].sort(byNewest));
}
