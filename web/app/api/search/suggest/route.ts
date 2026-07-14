import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_CARDS, MOCK_SETS } from '@/lib/data';
import { FEATURED_SET_CODES } from '@/lib/constants';
import { mapRawSet } from '@/lib/set-map';
import { getSetShortName } from '@/lib/set-names';
import { isDisplayableRarity, normalizeRarity } from '@/lib/rarity';

export async function GET(request: NextRequest) {
  const q = (request.nextUrl.searchParams.get('q') || '').trim();
  const limit = Math.min(parseInt(request.nextUrl.searchParams.get('limit') || '8', 10), 12);

  if (!q) {
    return NextResponse.json({ cards: [], sets: [] });
  }

  const pattern = `%${q}%`;

  try {
    const supabase = getSupabaseServer();

    const { data: featuredSets } = await supabase
      .from('card_sets')
      .select('id, set_code, name_kr, name_jp, name_en, released_at, image_url, prices_box ( region, price_krw )')
      .in('set_code', [...FEATURED_SET_CODES]);

    const sets = (featuredSets || [])
      .map(s => mapRawSet(s))
      .filter(s => s.name.includes(q) || s.code.toLowerCase().includes(q.toLowerCase()))
      .slice(0, 3)
      .map(s => ({ id: s.id, name: s.name, code: s.code }));

    const featuredSetIds = (featuredSets || []).map(s => s.id);
    if (featuredSetIds.length === 0) throw new Error('no sets');

    const { data: cards, error } = await supabase
      .from('cards')
      .select(`id, name_kr, name_jp, name_en, rarity, card_sets ( set_code, name_kr )`)
      .in('set_id', featuredSetIds)
      .or(`name_kr.ilike.${pattern},name_jp.ilike.${pattern},name_en.ilike.${pattern}`)
      .order('rarity_rank', { ascending: false })
      .limit(limit);

    if (error) throw error;

    const cardResults = (cards || [])
      .filter(c => isDisplayableRarity((c.rarity as string) || ''))
      .map(c => {
        const set = Array.isArray(c.card_sets) ? c.card_sets[0] : c.card_sets;
        const setCode = (set as { set_code?: string; name_kr?: string } | null)?.set_code || '';
        const setName = getSetShortName(setCode, (set as { name_kr?: string } | null)?.name_kr || '');
        return {
          id: String(c.id),
          name: (c.name_kr as string) || (c.name_jp as string) || (c.name_en as string) || '',
          rarity: normalizeRarity((c.rarity as string) || ''),
          set: setName,
        };
      });

    return NextResponse.json({ cards: cardResults, sets });
  } catch {
    const featuredCodes = FEATURED_SET_CODES as readonly string[];
    const sets = MOCK_SETS
      .filter(s => featuredCodes.includes(s.code) && s.name.includes(q))
      .slice(0, 3)
      .map(s => ({ id: s.id, name: s.name, code: s.code }));

    const cards = MOCK_CARDS
      .filter(c => featuredCodes.includes(c.setCode) && isDisplayableRarity(c.rarity))
      .filter(c => c.name.includes(q) || c.enName.toLowerCase().includes(q.toLowerCase()) || c.set.includes(q))
      .slice(0, limit)
      .map(c => ({ id: c.id, name: c.name, rarity: c.rarity, set: c.set }));

    return NextResponse.json({ cards, sets });
  }
}
