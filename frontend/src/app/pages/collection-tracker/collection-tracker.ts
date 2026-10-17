import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';
import { Collection } from '../../interfaces/Collection';
import { CollectionService } from '../../services/collection.service';

type Sort = 'newest' | 'highest' | 'lowest';

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

  sort = signal<Sort>('newest');
  private collections = toSignal(
    inject(CollectionService).list().pipe(catchError(() => of(null))),
    { initialValue: [] as Collection[] | null },
  );
  failed = computed(() => this.collections() === null);
  sorted = computed(() => {
    const list = [...(this.collections() ?? [])];
    const by = {
      newest: byNewest,
      highest: (a: Collection, b: Collection) => percent(b) - percent(a) || byNewest(a, b),
      lowest: (a: Collection, b: Collection) => percent(a) - percent(b) || byNewest(a, b),
    }[this.sort()];
    return list.sort(by);
  });

  onSort(value: string): void {
    this.sort.set(value as Sort);
  }
}
