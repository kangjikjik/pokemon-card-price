import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_CARDS, type Card } from '@/lib/data';
import { calcRepresentativePrice } from '@/lib/price-calc';
import { FEATURED_SET_CODES } from '@/lib/constants';
import { getSetShortName } from '@/lib/set-names';
import { compareCardsByRarity, isDisplayableRarity, normalizeRarity } from '@/lib/rarity';
import { matchesSearchQuery, searchIlikePattern } from '@/lib/search';

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

  const set = raw.card_sets as { id: number; set_code: string; name_kr: string; name_en: string } | null;

  const kr = calcRepresentativePrice(pricesKR);
  const jp = calcRepresentativePrice(pricesJP);

  return {
    id: String(raw.id),
    name: (raw.name_kr as string) || (raw.name_jp as string) || (raw.name_en as string) || '알 수 없음',
    enName: (raw.name_en as string) || '',
    set: getSetShortName(set?.set_code || '', set?.name_kr || ''),
    setCode: set?.set_code || '',
    setId: set?.id != null ? String(set.id) : '',
    number: (raw.card_number as string) || '',
    rarity: normalizeRarity((raw.rarity as string) || ''),
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

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q') || '';
  const rarity = searchParams.get('rarity') || '';
  const sort = searchParams.get('sort') || 'rarity_desc';
  const page = parseInt(searchParams.get('page') || '1');
  const limit = Math.min(parseInt(searchParams.get('limit') || '10000', 10), 15000);

  try {
    const supabase = getSupabaseServer();

    const { data: featuredSets } = await supabase
      .from('card_sets')
      .select('id')
      .in('set_code', [...FEATURED_SET_CODES]);

    const featuredSetIds = (featuredSets || []).map(s => s.id);
    if (featuredSetIds.length === 0) throw new Error('No featured sets');

    const selectFields = `
        id, name_kr, name_jp, name_en, rarity, rarity_rank, image_url, image_color, card_number,
        card_sets ( id, set_code, name_kr, name_en, name_jp ),
        prices_kr ( price_krw, fetched_at ),
        prices_jp ( price_krw, price_jpy, fetched_at )
      `;

    // Supabase는 요청당 최대 1000건 → 전체 조회 시 배치로 가져옴
    const BATCH = 1000;
    const allRows: Record<string, unknown>[] = [];
    let offset = (page - 1) * limit;

    while (allRows.length < limit) {
      const batchSize = Math.min(BATCH, limit - allRows.length);
      let query = supabase
        .from('cards')
        .select(selectFields)
        .in('set_id', featuredSetIds);

      if (q) {
        const pattern = searchIlikePattern(q);
        query = query.or(`name_kr.ilike.${pattern},name_jp.ilike.${pattern},name_en.ilike.${pattern}`);
      }
      if (rarity) query = query.eq('rarity', rarity);
      query = query.order('rarity_rank', { ascending: false }).order('card_number', { ascending: true });

      const { data, error } = await query.range(offset, offset + batchSize - 1);
      if (error) throw error;
      if (!data || data.length === 0) break;

      allRows.push(...(data as Record<string, unknown>[]));
      if (data.length < batchSize) break;
      offset += batchSize;
    }

    if (allRows.length === 0) throw new Error('No data');

    const cards = allRows
      .map(d => transformCard(d))
      .filter(c => isDisplayableRarity(c.rarity));

    if (sort === 'price_asc') cards.sort((a, b) => a.priceKR - b.priceKR);
    else if (sort === 'price_desc') cards.sort((a, b) => b.priceKR - a.priceKR);
    else cards.sort(compareCardsByRarity);

    return NextResponse.json({ data: cards, total: cards.length, source: 'db' });
  } catch {
    const featuredCodes = FEATURED_SET_CODES as readonly string[];
    let result = MOCK_CARDS.filter(c => featuredCodes.includes(c.setCode) && isDisplayableRarity(c.rarity));
    if (q) result = result.filter(c => matchesSearchQuery(c.name, q) || matchesSearchQuery(c.enName, q));
    if (rarity) result = result.filter(c => c.rarity === rarity);
    if (sort === 'price_asc') result.sort((a, b) => a.priceKR - b.priceKR);
    else if (sort === 'price_desc') result.sort((a, b) => b.priceKR - a.priceKR);
    else result.sort(compareCardsByRarity);

    return NextResponse.json({ data: result, source: 'mock' });
  }
}
