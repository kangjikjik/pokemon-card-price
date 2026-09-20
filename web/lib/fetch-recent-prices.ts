import type { SupabaseClient } from '@supabase/supabase-js';

export type PriceRow = { price_krw: number; fetched_at?: string; source?: string };

type RawPriceRow = {
  card_id: number;
  price_krw: number;
  fetched_at: string | null;
  source: string | null;
};

function isBunjangSource(source?: string | null): boolean {
  if (!source) return false;
  return (
    source === 'bunjang:sold' ||
    source === 'bunjang:listing' ||
    source === 'bunjang:sold+listing' ||
    source === 'sold:bunjang' ||
    source === 'listing:bunjang' ||
    source === 'sold+listing:bunjang' ||
    /^sold:bunjang:\d+/.test(source) ||
    /^listing:bunjang:\d+/.test(source)
  );
}

function comparePriceRows(a: PriceRow, b: PriceRow): number {
  const ta = a.fetched_at || '';
  const tb = b.fetched_at || '';
  if (ta !== tb) return tb.localeCompare(ta);
  return (a.source || '').localeCompare(b.source || '');
}

async function fetchPriceRowsForCards(
  supabase: SupabaseClient,
  table: 'prices_kr' | 'prices_jp',
  cardIds: number[],
  sinceIso: string,
): Promise<RawPriceRow[]> {
  const rows: RawPriceRow[] = [];
  for (let offset = 0; ; offset += 1000) {
    const { data } = await supabase
      .from(table)
      .select('card_id, price_krw, fetched_at, source')
      .in('card_id', cardIds)
      .gt('price_krw', 0)
      .gte('fetched_at', sinceIso)
      .order('fetched_at', { ascending: false })
      .range(offset, offset + 999);

    const page = (data || []) as RawPriceRow[];
    rows.push(...page);
    if (page.length < 1000) break;
  }
  return rows;
}

function topRowsPerCard(
  rows: RawPriceRow[],
  cardIds: number[],
  perCardMax: number,
): Map<number, PriceRow[]> {
  const byCard = new Map<number, PriceRow[]>();
  for (const id of cardIds) {
    byCard.set(id, []);
  }

  for (const row of rows) {
    if (!isBunjangSource(row.source)) continue;
    const bucket = byCard.get(row.card_id);
    if (!bucket) continue;
    bucket.push({
      price_krw: row.price_krw,
      fetched_at: row.fetched_at ?? undefined,
      source: row.source ?? undefined,
    });
  }

  const out = new Map<number, PriceRow[]>();
  for (const id of cardIds) {
    const sorted = [...(byCard.get(id) || [])].sort(comparePriceRows);
    out.set(id, sorted.slice(0, perCardMax));
  }
  return out;
}

/** 카드별 최근 시세만 조회 (세트 SSR CPU 한도 방지). */
export async function fetchRecentPricesByCard(
  supabase: SupabaseClient,
  cardIds: number[],
  opts?: { daysBack?: number; maxRows?: number; perCardMax?: number },
): Promise<Map<number, { kr: PriceRow[]; jp: PriceRow[] }>> {
  const out = new Map<number, { kr: PriceRow[]; jp: PriceRow[] }>();
  if (!cardIds.length) return out;

  for (const id of cardIds) {
    out.set(id, { kr: [], jp: [] });
  }

  const daysBack = opts?.daysBack ?? 7;
  const perCardMax = opts?.perCardMax ?? 12;
  const since = new Date();
  since.setDate(since.getDate() - daysBack);
  const sinceIso = since.toISOString();

  const [krRows, jpRows] = await Promise.all([
    fetchPriceRowsForCards(supabase, 'prices_kr', cardIds, sinceIso),
    fetchPriceRowsForCards(supabase, 'prices_jp', cardIds, sinceIso),
  ]);

  const krByCard = topRowsPerCard(krRows, cardIds, perCardMax);
  const jpByCard = topRowsPerCard(jpRows, cardIds, perCardMax);

  for (const id of cardIds) {
    out.set(id, {
      kr: krByCard.get(id) || [],
      jp: jpByCard.get(id) || [],
    });
  }

  return out;
}
