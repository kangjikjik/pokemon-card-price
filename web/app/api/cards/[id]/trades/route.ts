import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { isViewableSetCode } from '@/lib/constants';
import { sameArtPriceIds } from '@/lib/same-art-price-groups';

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

function dedupeTrades(records: TradeRecord[]): TradeRecord[] {
  const map = new Map<string, TradeRecord>();
  for (const r of records) {
    const pid = extractBunjangPid(r.source);
    if (!pid) continue;
    const key = `bunjang:${pid}`;
    const existing = map.get(key);
    if (!existing) {
      map.set(key, r);
      continue;
    }
    const hasTs = extractBunjangTs(r.source) !== null;
    const existingHasTs = extractBunjangTs(existing.source) !== null;
    if (hasTs && !existingHasTs) map.set(key, r);
  }
  return [...map.values()];
}

function finalizeTrades(
  raw: { price_krw: number; source: string | null; fetched_at: string | null }[],
): TradeRecord[] {
  const mapped: TradeRecord[] = [];
  for (const r of raw) {
    const fa = r.fetched_at || '';
    const parsed = parseBunjangTrade(r.source || '', fa);
    if (parsed) mapped.push({ ...parsed, price_krw: r.price_krw });
  }
  return dedupeTrades(mapped)
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

    const priceIds = [...sameArtPriceIds(numericId)];
    const bunjangFilter = 'source.like.sold:bunjang:%,source.like.listing:bunjang:%';

    const [krRes, jpRes] = await Promise.all([
      supabase
        .from('prices_kr')
        .select('price_krw, source, fetched_at')
        .in('card_id', priceIds)
        .gt('price_krw', 0)
        .or(bunjangFilter)
        .order('fetched_at', { ascending: false })
        .limit(300),
      supabase
        .from('prices_jp')
        .select('price_krw, source, fetched_at')
        .in('card_id', priceIds)
        .gt('price_krw', 0)
        .or(bunjangFilter)
        .order('fetched_at', { ascending: false })
        .limit(300),
    ]);

    return NextResponse.json({
      kr: finalizeTrades(krRes.data || []),
      jp: finalizeTrades(jpRes.data || []),
    });
  } catch {
    return NextResponse.json({ kr: [], jp: [] });
  }
}
