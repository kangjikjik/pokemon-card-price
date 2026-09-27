import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_SETS, MOCK_CARDS } from '@/lib/data';
import { isViewableSetCode } from '@/lib/constants';
import { fetchRecentPricesByCard } from '@/lib/fetch-recent-prices';
import { fetchRecentBoxPricesBySet } from '@/lib/fetch-recent-box-prices';

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    const supabase = getSupabaseServer();

    // 세트 정보 + 박스 시세
    const { data: setRaw, error: setError } = await supabase
      .from('card_sets')
      .select(`id, set_code, name_kr, name_en, released_at`)
      .eq('id', id)
      .single();

    if (setError) throw setError;
    if (!isViewableSetCode(setRaw.set_code)) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const numericSetId = parseInt(id, 10);
    const boxMap = await fetchRecentBoxPricesBySet(supabase, [numericSetId]);
    const setData = { ...setRaw, prices_box: boxMap.get(numericSetId) ?? [] };

    // 수록 카드 목록 + 최신 시세
    const { data: cardsData, error: cardsError } = await supabase
      .from('cards')
      .select(`
        id, name_kr, name_en, rarity, rarity_rank, image_color, card_number
      `)
      .eq('set_id', id)
      .order('rarity_rank', { ascending: false });

    if (cardsError) throw cardsError;

    const cardIds = (cardsData || []).map(c => c.id as number);
    const priceMap = await fetchRecentPricesByCard(
      supabase,
      cardIds,
      { daysBack: 14 },
    );
    const cardsWithPrices = (cardsData || []).map(c => {
      const p = priceMap.get(c.id as number);
      return {
        ...c,
        prices_kr: p?.kr ?? [],
        prices_jp: p?.jp ?? [],
      };
    });

    return NextResponse.json({ set: setData, cards: cardsWithPrices, source: 'db' });
  } catch {
    const set = MOCK_SETS.find(s => s.id === id) || MOCK_SETS[0];
    const cards = MOCK_CARDS.filter(c => c.set === set.name);
    return NextResponse.json({ set, cards, source: 'mock' });
  }
}
