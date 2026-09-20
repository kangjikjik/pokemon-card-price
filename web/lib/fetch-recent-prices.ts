import type { SupabaseClient } from '@supabase/supabase-js';

export type PriceRow = { price_krw: number; fetched_at?: string; source?: string };

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
  const maxRows = opts?.maxRows ?? Math.min(cardIds.length * perCardMax, 800);
  const since = new Date();
  since.setDate(since.getDate() - daysBack);
  const sinceIso = since.toISOString();

  /** summary 우선 — 개별 row는 800건 한도에 밀리므로 제외 (calc에서 summary 사용) */
  const summaryFilter =
    'source.eq.sold:bunjang,source.eq.listing:bunjang,source.eq.sold:bunjang+snkrdunk,source.eq.listing:bunjang+kream,source.eq.sold:snkrdunk';

  const [krRes, jpRes] = await Promise.all([
    supabase
      .from('prices_kr')
      .select('card_id, price_krw, fetched_at, source')
      .in('card_id', cardIds)
      .gt('price_krw', 0)
      .gte('fetched_at', sinceIso)
      .or(summaryFilter)
      .order('fetched_at', { ascending: false })
      .limit(maxRows),
    supabase
      .from('prices_jp')
      .select('card_id, price_krw, fetched_at, source')
      .in('card_id', cardIds)
      .gt('price_krw', 0)
      .gte('fetched_at', sinceIso)
      .or(summaryFilter)
      .order('fetched_at', { ascending: false })
      .limit(maxRows),
  ]);

  for (const row of krRes.data || []) {
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
