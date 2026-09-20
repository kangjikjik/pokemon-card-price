import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_CARDS, type Card } from '@/lib/data';
import { calcRepresentativePrice } from '@/lib/price-calc';
import { fetchRecentPricesByCard } from '@/lib/fetch-recent-prices';
import { CARDS_LIST_SET_CODES, FEATURED_SET_CODES, isViewableSetCode } from '@/lib/constants';

export const dynamic = 'force-dynamic';

const SET_COLORS: Record<string, string> = {
  SV2a: 'from-green-500 to-emerald-700',
  SV2D: 'from-purple-500 to-fuchsia-700',
  S12a: 'from-slate-800 to-slate-950',
  SV4a: 'from-cyan-400 to-blue-600',
  S11:  'from-indigo-700 to-purple-900',
  S12:  'from-blue-500 to-indigo-700',
};

function transformCard(raw: Record<string, unknown>): Card {
  const pricesKR = Array.isArray(raw.prices_kr)
    ? (raw.prices_kr as { price_krw: number; fetched_at: string }[])
    : [];
  const pricesJP = Array.isArray(raw.prices_jp)
    ? (raw.prices_jp as { price_krw: number; price_jpy: number; fetched_at: string }[])
    : [];
  const set = raw.card_sets as { id: number; set_code: string; name_kr: string; name_en: string; released_at: string } | null;

  const kr = calcRepresentativePrice(pricesKR);
  const jp = calcRepresentativePrice(pricesJP);

  return {
    id: String(raw.id),
    name: (raw.name_kr as string) || (raw.name_jp as string) || (raw.name_en as string) || '알 수 없음',
    enName: (raw.name_en as string) || '',
    set: set?.name_kr || '',
    setCode: set?.set_code || '',
    setId: set?.id != null ? String(set.id) : '',
    number: (raw.card_number as string) || '',
    rarity: (raw.rarity as string) || '',
    rarityRank: (raw.rarity_rank as number) || 0,
    imageUrl: (raw.image_url as string) || '',
    imageColor: (raw.image_color as string) || SET_COLORS[set?.set_code || ''] || 'from-slate-400 to-slate-600',
    priceKR: kr.price,
    priceJP: jp.price,
    trendKR: kr.trend,
    trendJP: jp.trend,
    historyKR: kr.history,
    historyJP: jp.history,
  };
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const numericId = parseInt(id);

  try {
    if (isNaN(numericId)) throw new Error('Non-numeric ID');

    const supabase = getSupabaseServer();

    const { data: cardRow, error } = await supabase
      .from('cards')
      .select(`
        id, name_kr, name_jp, name_en, rarity, rarity_rank, image_url, image_color, card_number,
        card_sets ( id, set_code, name_kr, name_jp, name_en, released_at )
      `)
      .eq('id', numericId)
      .single();

    if (error) throw error;
    if (!cardRow) throw new Error('Not found');

    const setRaw = cardRow.card_sets as { set_code: string } | { set_code: string }[] | null;
    const setCode = (Array.isArray(setRaw) ? setRaw[0] : setRaw)?.set_code || '';
    if (!isViewableSetCode(setCode)) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const priceMap = await fetchRecentPricesByCard(
      supabase,
      [numericId],
      { daysBack: 90, perCardMax: 12 },
    );
    const prices = priceMap.get(numericId) ?? { kr: [], jp: [] };

    const payload = {
      ...cardRow,
      prices_kr: prices.kr,
      prices_jp: prices.jp,
    };

    return NextResponse.json({ data: transformCard(payload as Record<string, unknown>), source: 'db' });
  } catch {
    const viewableCodes = CARDS_LIST_SET_CODES as readonly string[];
    const card = MOCK_CARDS.find(c => c.id === id && viewableCodes.includes(c.setCode));
    if (!card) return NextResponse.json({ error: 'Not found' }, { status: 404 });
    return NextResponse.json({ data: card, source: 'mock' });
  }
}
