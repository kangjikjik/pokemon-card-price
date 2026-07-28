import type { SupabaseClient } from '@supabase/supabase-js';
import { latestPriceKrw } from '@/lib/price-calc';

const PRICE_LOOKBACK_DAYS = 90;

/** 최근 90일 KR 시세만 배치 조회 → 카드별 최신가 (join 부하↓) */
export async function buildLatestKrPriceMap(
  supabase: SupabaseClient,
  cardIds: number[],
): Promise<Map<number, number>> {
  const map = new Map<number, number>();
  if (cardIds.length === 0) return map;

  const since = new Date();
  since.setDate(since.getDate() - PRICE_LOOKBACK_DAYS);
  const sinceIso = since.toISOString();

  const BATCH = 500;
  for (let i = 0; i < cardIds.length; i += BATCH) {
    const chunk = cardIds.slice(i, i + BATCH);
    const { data, error } = await supabase
      .from('prices_kr')
      .select('card_id, price_krw, fetched_at')
      .in('card_id', chunk)
      .gte('fetched_at', sinceIso)
      .order('fetched_at', { ascending: false });

    if (error) throw error;

    const byCard = new Map<number, { price_krw: number; fetched_at: string }[]>();
    for (const row of data || []) {
      const cid = row.card_id as number;
      const list = byCard.get(cid) || [];
      list.push({
        price_krw: row.price_krw as number,
        fetched_at: (row.fetched_at as string) || '',
      });
      byCard.set(cid, list);
    }

    for (const [cid, prices] of byCard) {
      map.set(cid, latestPriceKrw(prices));
    }
  }

  return map;
}

export function viewCountFromRow(row: Record<string, unknown>): number {
  const v = row.view_count;
  return typeof v === 'number' && Number.isFinite(v) ? v : 0;
}
