import type { SupabaseClient } from '@supabase/supabase-js';
import { isTradeDetailSource, latestPriceKrw } from '@/lib/price-calc';

const PRICE_LOOKBACK_DAYS = 14;
const PER_CARD_MAX = 4;

/** 개별 거래 PID row는 빼고 일별 요약만. 전량 조회는 Worker 1102. */
const SUMMARY_SOURCES = [
  'bunjang:sold',
  'bunjang:sold+listing',
  'bunjang-jp:sold',
  'sold+listing:bunjang',
  'sold:bunjang',
  'bunjang:listing',
  'bunjang-jp:listing',
  'listing:bunjang',
];

/** 최근 KR 시세만 배치 조회 → 카드별 최신가 (join·row 폭주 방지) */
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
    const rowLimit = Math.min(chunk.length * PER_CARD_MAX, 800);
    const { data, error } = await supabase
      .from('prices_kr')
      .select('card_id, price_krw, fetched_at, source')
      .in('card_id', chunk)
      .in('source', SUMMARY_SOURCES)
      .gte('fetched_at', sinceIso)
      .order('fetched_at', { ascending: false })
      .limit(rowLimit);

    if (error) throw error;

    const byCard = new Map<number, { price_krw: number; fetched_at: string; source?: string }[]>();
    for (const row of data || []) {
      if (isTradeDetailSource(row.source as string)) continue;
      const cid = row.card_id as number;
      const list = byCard.get(cid) || [];
      if (list.length >= PER_CARD_MAX) continue;
      list.push({
        price_krw: row.price_krw as number,
        fetched_at: (row.fetched_at as string) || '',
        source: (row.source as string) || '',
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
