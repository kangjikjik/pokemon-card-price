import type { SupabaseClient } from '@supabase/supabase-js';
import { isBoxTradeDetailSource } from '@/lib/price-calc';

export type BoxPriceRow = { region: string; price_krw: number; fetched_at?: string; source?: string };

const BOX_DETAIL_OR =
  'source.like.bunjang:sold:%,source.like.bunjang:listing:%,source.like.bunjang-jp:sold:%,source.like.bunjang-jp:listing:%';

/** 세트별 박스 시세. 저장된 거래 내역을 날짜로 자르지 않는다. */
export async function fetchRecentBoxPricesBySet(
  supabase: SupabaseClient,
  setIds: number[],
  opts?: { perSetMax?: number; maxRows?: number },
): Promise<Map<number, BoxPriceRow[]>> {
  const out = new Map<number, BoxPriceRow[]>();
  if (!setIds.length) return out;

  for (const id of setIds) {
    out.set(id, []);
  }

  const perSetMax = opts?.perSetMax ?? 30;

  const rows: Record<string, unknown>[] = [];
  const maxRows = opts?.maxRows ?? 20000;
  for (let offset = 0; offset < maxRows; offset += 1000) {
    const { data } = await supabase
      .from('prices_box')
      .select('set_id, region, price_krw, fetched_at, source')
      .in('set_id', setIds)
      .gt('price_krw', 0)
      .or(BOX_DETAIL_OR)
      .order('fetched_at', { ascending: false })
      .range(offset, offset + 999);
    rows.push(...((data || []) as Record<string, unknown>[]));
    if (!data || data.length < 1000) break;
  }

  for (const row of rows) {
    const sid = row.set_id as number;
    const bucket = out.get(sid);
    if (!bucket) continue;
    const region = row.region as string;
    const regionCount = bucket.filter((item) => item.region === region).length;
    if (regionCount >= perSetMax) continue;
    const source = row.source as string | undefined;
    if (!source || !isBoxTradeDetailSource(source)) continue;
    bucket.push({
      region,
      price_krw: row.price_krw as number,
      fetched_at: row.fetched_at as string | undefined,
      source,
    });
  }

  return out;
}
