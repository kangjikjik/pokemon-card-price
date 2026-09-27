import type { SupabaseClient } from '@supabase/supabase-js';
import { isBoxTradeDetailSource } from '@/lib/price-calc';

export type BoxPriceRow = { region: string; price_krw: number; fetched_at?: string; source?: string };

/** 세트별 최근 박스 시세 조회. 대표 요약 행과 개별 거래 행을 함께 사용한다. */
export async function fetchRecentBoxPricesBySet(
  supabase: SupabaseClient,
  setIds: number[],
  opts?: { daysBack?: number; perSetMax?: number; maxRows?: number },
): Promise<Map<number, BoxPriceRow[]>> {
  const out = new Map<number, BoxPriceRow[]>();
  if (!setIds.length) return out;

  for (const id of setIds) {
    out.set(id, []);
  }

  const daysBack = opts?.daysBack ?? 7;
  const perSetMax = opts?.perSetMax ?? 30;
  const since = new Date();
  since.setDate(since.getDate() - daysBack);

  // Supabase 기본 응답 제한을 피하되, 세트마다 요청하지 않고
  // 1000행 단위로만 페이지 조회해 서버 렌더링 시간을 제한한다.
  const rows: Record<string, unknown>[] = [];
  const maxRows = opts?.maxRows ?? 1500;
  for (let offset = 0; offset < maxRows; offset += 1000) {
    const { data } = await supabase
      .from('prices_box')
      .select('set_id, region, price_krw, fetched_at, source')
      .in('set_id', setIds)
      .gt('price_krw', 0)
      .gte('fetched_at', since.toISOString())
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
    // 대표 요약 행은 시세 추이·대표가 계산에 사용하고,
    // PID가 있는 개별 행은 거래내역과 보조 계산에 사용한다.
    if (
      !source ||
      (
        !isBoxTradeDetailSource(source) &&
        !source.endsWith(':sold') &&
        !source.endsWith(':listing') &&
        !source.endsWith(':sold+listing') &&
        source !== 'sold+listing:bunjang'
      )
    ) {
      continue;
    }
    bucket.push({
      region,
      price_krw: row.price_krw as number,
      fetched_at: row.fetched_at as string | undefined,
      source,
    });
  }

  return out;
}
