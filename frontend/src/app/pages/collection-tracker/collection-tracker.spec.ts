import { byNewest, percent } from './collection-tracker';

const c = (prefix: string, owned = 0, total: number | null = 10) => ({ prefix, owned, total });

describe('collection-tracker', () => {
  it('ordena mais nova primeiro: OP, EB, ST, número decrescente', () => {
    const sorted = [c('ST01'), c('OP01'), c('EB03'), c('OP17'), c('EB01')].sort(byNewest);
    expect(sorted.map((x) => x.prefix)).toEqual(['OP17', 'OP01', 'EB03', 'EB01', 'ST01']);
  });

  it('calcula % e trata total ausente', () => {
    expect(percent(c('OP01', 5, 10))).toBe(50);
    expect(percent(c('OP01', 5, null))).toBe(0);
  });
});
