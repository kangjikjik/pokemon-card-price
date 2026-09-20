import type { SupabaseClient } from '@supabase/supabase-js';

export type PriceRow = { price_krw: number; fetched_at?: string; source?: string };

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
  const maxRows = opts?.maxRows ?? cardIds.length * perCardMax;
  const since = new Date();
  since.setDate(since.getDate() - daysBack);
  const sinceIso = since.toISOString();

  const [krRes, jpRes] = await Promise.all([
    supabase
      .from('prices_kr')
      .select('card_id, price_krw, fetched_at, source')
      .in('card_id', cardIds)
      .gt('price_krw', 0)
      .gte('fetched_at', sinceIso)
      .order('card_id', { ascending: true })
      .order('fetched_at', { ascending: false })
      .order('source', { ascending: true })
      .limit(maxRows),
    supabase
      .from('prices_jp')
      .select('card_id, price_krw, fetched_at, source')
      .in('card_id', cardIds)
      .gt('price_krw', 0)
      .gte('fetched_at', sinceIso)
      .order('card_id', { ascending: true })
      .order('fetched_at', { ascending: false })
      .order('source', { ascending: true })
      .limit(maxRows),
  ]);

  for (const row of krRes.data || []) {
    if (!isBunjangSource(row.source)) continue;
    const bucket = out.get(row.card_id as number);
    if (bucket && bucket.kr.length < perCardMax) {
      bucket.kr.push({
        price_krw: row.price_krw,
        fetched_at: row.fetched_at ?? undefined,
        source: row.source ?? undefined,
      });
    }
  }
  for (const row of jpRes.data || []) {
    if (!isBunjangSource(row.source)) continue;
    const bucket = out.get(row.card_id as number);
    if (bucket && bucket.jp.length < perCardMax) {
      bucket.jp.push({
        price_krw: row.price_krw,
        fetched_at: row.fetched_at ?? undefined,
        source: row.source ?? undefined,
      });
    }
  }

  return out;
}
