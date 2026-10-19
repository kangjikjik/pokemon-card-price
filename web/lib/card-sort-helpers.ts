import type { SupabaseClient } from '@supabase/supabase-js';
import { averageTradeDetailPrice } from '@/lib/price-calc';

const DETAIL_SOURCE_OR = 'source.like.sold:bunjang:%,source.like.listing:bunjang:%';

/** KR 거래 내역 평균으로 가격순 정렬. 14일 컷을 쓰지 않는다. */
export async function buildLatestKrPriceMap(
  supabase: SupabaseClient,
  cardIds: number[],
): Promise<Map<number, number>> {
  const map = new Map<number, number>();
  if (cardIds.length === 0) return map;

  const BATCH = 80;
  for (let i = 0; i < cardIds.length; i += BATCH) {
    const chunk = cardIds.slice(i, i + BATCH);
    const byCard = new Map<number, { price_krw: number; fetched_at?: string; source?: string }[]>();
    for (let offset = 0, page = 0; page < 8; offset += 1000, page += 1) {
      const { data, error } = await supabase
        .from('prices_kr')
        .select('card_id, price_krw, fetched_at, source')
        .in('card_id', chunk)
        .gt('price_krw', 0)
        .or(DETAIL_SOURCE_OR)
        .order('fetched_at', { ascending: false })
        .range(offset, offset + 999);
      if (error) throw error;
      const pageRows = data || [];
      for (const row of pageRows) {
        const cid = row.card_id as number;
        const list = byCard.get(cid) || [];
        list.push({
          price_krw: row.price_krw as number,
          fetched_at: (row.fetched_at as string) || '',
          source: (row.source as string) || '',
        });
        byCard.set(cid, list);
      }
      if (pageRows.length < 1000) break;
    }

    for (const [cid, prices] of byCard) {
      map.set(cid, averageTradeDetailPrice(prices));
    }
  }

  return map;
}

export function viewCountFromRow(row: Record<string, unknown>): number {
  const v = row.view_count;
  return typeof v === 'number' && Number.isFinite(v) ? v : 0;
}
