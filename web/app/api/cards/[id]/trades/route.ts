import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { isViewableSetCode } from '@/lib/constants';

export interface TradeRecord {
  price_krw: number;
  source: string;
  fetched_at: string;
  traded_at: string;
  platform: string;
  label: string;
  url?: string;
}

export interface TradesResponse {
  kr: TradeRecord[];
  jp: TradeRecord[];
}

const MAX_TRADES = 100;

/** MEGA(MG*) — JP 거래내역은 번개장터만 (SNKRDUNK 제외) */
function isMegaSet(setCode: string): boolean {
  return setCode.toUpperCase().startsWith('MG');
}

function extractBunjangPid(source: string): string | null {
  const parts = source.split(':');
  if (parts.length >= 3 && parts[1] === 'bunjang' && /^\d+$/.test(parts[2])) return parts[2];
  return null;
}

function extractBunjangTs(source: string): number | null {
  const parts = source.split(':');
  if (parts.length >= 4 && parts[1] === 'bunjang') {
    const ts = parseInt(parts[3], 10);
    return Number.isNaN(ts) || ts <= 0 ? null : ts;
  }
  return null;
}

function extractSnkrdunkPid(source: string): string | null {
  const parts = source.split(':');
  if (parts.length >= 3 && parts[1] === 'snkrdunk' && /^\d+$/.test(parts[2])) return parts[2];
  return null;
}

function extractSnkrdunkDate(source: string): string | null {
  const parts = source.split(':');
  if (parts.length >= 4 && parts[1] === 'snkrdunk' && /^\d{4}-\d{2}-\d{2}$/.test(parts[3])) {
    return parts[3];
  }
  return null;
}

function parseBunjangTrade(source: string, fetchedAt: string): TradeRecord | null {
  const pid = extractBunjangPid(source);
  if (!pid) return null;
  const isSold = source.startsWith('sold:bunjang:');
  const isListing = source.startsWith('listing:bunjang:');
  if (!isSold && !isListing) return null;
  const ts = extractBunjangTs(source);
  return {
    price_krw: 0,
    source,
    fetched_at: fetchedAt,
    platform: '번개장터',
    label: isSold ? '거래완료' : '판매중(호가)',
    url: `https://bunjang.co.kr/products/${pid}`,
    traded_at: ts ? new Date(ts * 1000).toISOString() : fetchedAt,
  };
}

function parseSnkSold(source: string, fetchedAt: string, priceKrw: number): TradeRecord | null {
  const pid = extractSnkrdunkPid(source);
  if (!pid || !source.startsWith('sold:snkrdunk:')) return null;
  const date = extractSnkrdunkDate(source);
  return {
    price_krw: priceKrw,
    source,
    fetched_at: fetchedAt,
    platform: 'SNKRDUNK',
    label: '거래완료',
    url: `https://snkrdunk.com/apparels/${pid}`,
    traded_at: date ? new Date(`${date}T12:00:00+09:00`).toISOString() : fetchedAt,
  };
}

function dedupeTrades(records: TradeRecord[]): TradeRecord[] {
  const map = new Map<string, TradeRecord>();
  for (const r of records) {
    const bPid = extractBunjangPid(r.source);
    const snkPid = extractSnkrdunkPid(r.source);
    const key = bPid
      ? `bunjang:${bPid}`
      : `snk:${snkPid}:${extractSnkrdunkDate(r.source) ?? ''}`;
    const existing = map.get(key);
    if (!existing) {
      map.set(key, r);
      continue;
    }
    if (bPid) {
      const hasTs = extractBunjangTs(r.source) !== null;
      const existingHasTs = extractBunjangTs(existing.source) !== null;
      if (hasTs && !existingHasTs) map.set(key, r);
      continue;
    }
    // SNK: 동일 상품·날짜는 1건만 (가격은 중간값에 가까운 쪽 유지)
    if (snkPid && r.price_krw > 0) {
      const mid = Math.round((existing.price_krw + r.price_krw) / 2);
      const keep =
        Math.abs(r.price_krw - mid) <= Math.abs(existing.price_krw - mid) ? r : existing;
      map.set(key, { ...keep, price_krw: mid });
    }
  }
  return [...map.values()];
}

function filterSnkOutliers(records: TradeRecord[]): TradeRecord[] {
  const snk = records.filter((r) => extractSnkrdunkPid(r.source));
  const rest = records.filter((r) => !extractSnkrdunkPid(r.source));
  if (snk.length < 3) return records;
  const prices = snk.map((r) => r.price_krw).sort((a, b) => a - b);
  const med = prices[Math.floor(prices.length / 2)];
  const cap = Math.max(Math.floor(med * 2.5), med + 30_000);
  return [...rest, ...snk.filter((r) => r.price_krw <= cap)];
}

function finalizeKr(raw: { price_krw: number; source: string | null; fetched_at: string | null }[]): TradeRecord[] {
  const mapped: TradeRecord[] = [];
  for (const r of raw) {
    const fa = r.fetched_at || '';
    const parsed = parseBunjangTrade(r.source || '', fa);
    if (parsed) mapped.push({ ...parsed, price_krw: r.price_krw });
  }
  return filterSnkOutliers(dedupeTrades(mapped))
    .sort((a, b) => new Date(b.traded_at).getTime() - new Date(a.traded_at).getTime())
    .slice(0, MAX_TRADES);
}

function finalizeJp(
  raw: { price_krw: number; source: string | null; fetched_at: string | null }[],
  bunjangOnly = false,
): TradeRecord[] {
  const mapped: TradeRecord[] = [];
  for (const r of raw) {
    const fa = r.fetched_at || '';
    const src = r.source || '';
    const bunjang = parseBunjangTrade(src, fa);
    if (bunjang) {
      mapped.push({ ...bunjang, price_krw: r.price_krw });
      continue;
    }
    if (!bunjangOnly) {
      const snk = parseSnkSold(src, fa, r.price_krw);
      if (snk) mapped.push(snk);
    }
  }
  return filterSnkOutliers(dedupeTrades(mapped))
    .sort((a, b) => new Date(b.traded_at).getTime() - new Date(a.traded_at).getTime())
    .slice(0, MAX_TRADES);
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const numericId = parseInt(id, 10);
  if (Number.isNaN(numericId)) {
    return NextResponse.json({ error: 'invalid id' }, { status: 400 });
  }

  try {
    const supabase = getSupabaseServer();

    const { data: card } = await supabase
      .from('cards')
      .select('id, card_number, card_sets ( set_code )')
      .eq('id', numericId)
      .single();

    if (!card) return NextResponse.json({ error: 'not found' }, { status: 404 });

    const setRaw = card.card_sets as { set_code: string } | { set_code: string }[] | null;
    const setCode = (Array.isArray(setRaw) ? setRaw[0] : setRaw)?.set_code || '';
    if (!isViewableSetCode(setCode)) {
      return NextResponse.json({ error: 'not found' }, { status: 404 });
    }

    const megaBunjangOnly = isMegaSet(setCode);
    const bunjangFilter = 'source.like.sold:bunjang:%,source.like.listing:bunjang:%';

    const [krRes, jpRes] = await Promise.all([
      supabase
        .from('prices_kr')
        .select('price_krw, source, fetched_at')
        .eq('card_id', numericId)
        .gt('price_krw', 0)
        .or(bunjangFilter)
        .order('fetched_at', { ascending: false })
        .limit(150),
      supabase
        .from('prices_jp')
        .select('price_krw, source, fetched_at')
        .eq('card_id', numericId)
        .gt('price_krw', 0)
        .or(megaBunjangOnly ? bunjangFilter : `${bunjangFilter},source.like.sold:snkrdunk:%`)
        .order('fetched_at', { ascending: false })
        .limit(150),
    ]);

    return NextResponse.json({
      kr: finalizeKr(krRes.data || []),
      jp: finalizeJp(jpRes.data || [], megaBunjangOnly),
    });
  } catch {
    return NextResponse.json({ kr: [], jp: [] });
  }
}
