import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_SETS, MOCK_CARDS } from '@/lib/data';
import { isFeaturedSetCode } from '@/lib/constants';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    const supabase = getSupabaseServer();

    // 세트 정보 + 박스 시세
    const { data: setData, error: setError } = await supabase
      .from('card_sets')
      .select(`
        id, set_code, name_kr, name_en, released_at,
        prices_box(region, price_krw, fetched_at)
      `)
      .eq('id', id)
      .single();

    if (setError) throw setError;
    if (!isFeaturedSetCode(setData.set_code)) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    // 수록 카드 목록 + 최신 시세
    const { data: cardsData, error: cardsError } = await supabase
      .from('cards')
      .select(`
        id, name_kr, name_en, rarity, rarity_rank, image_color, card_number,
        prices_kr(price_krw, fetched_at),
        prices_jp(price_krw, fetched_at)
      `)
      .eq('set_id', id)
      .order('rarity_rank', { ascending: false });

    if (cardsError) throw cardsError;

    return NextResponse.json({ set: setData, cards: cardsData, source: 'db' });
  } catch {
    const set = MOCK_SETS.find(s => s.id === id) || MOCK_SETS[0];
    const cards = MOCK_CARDS.filter(c => c.set === set.name);
    return NextResponse.json({ set, cards, source: 'mock' });
  }
}
