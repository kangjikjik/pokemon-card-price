import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_CARDS, MOCK_SETS } from '@/lib/data';
import { CARDS_LIST_SET_CODES } from '@/lib/constants';
import { mapRawSet } from '@/lib/set-map';
import { getSetShortName } from '@/lib/set-names';
import { isDisplayableRarity, normalizeRarity } from '@/lib/rarity';
import { cardNameSearchOr, matchesSearchQuery, setMatchesSearchQuery } from '@/lib/search';

const SEARCH_SET_CODES = [...CARDS_LIST_SET_CODES];

export async function GET(request: NextRequest) {
  const q = (request.nextUrl.searchParams.get('q') || '').trim();
  const limit = Math.min(parseInt(request.nextUrl.searchParams.get('limit') || '8', 10), 12);

  if (!q) {
    return NextResponse.json({ cards: [], sets: [] });
  }

  try {
    const supabase = getSupabaseServer();

    const { data: allSets } = await supabase
      .from('card_sets')
      .select('id, set_code, name_kr, name_jp, name_en, released_at, image_url, prices_box ( region, price_krw )')
      .in('set_code', SEARCH_SET_CODES);

    const sets = (allSets || [])
      .map(s => mapRawSet(s))
      .filter(s =>
        setMatchesSearchQuery(
          s.code,
          q,
          (allSets || []).find(r => r.set_code === s.code)?.name_kr,
        ),
      )
      .slice(0, 5)
      .map(s => ({ id: s.id, name: s.name, code: s.code }));

    const searchSetIds = (allSets || []).map(s => s.id);
    if (searchSetIds.length === 0) throw new Error('no sets');

    const matchingSetIds = (allSets || [])
      .filter(s => setMatchesSearchQuery(s.set_code || '', q, s.name_kr))
      .map(s => s.id);

    const cardFilter = cardNameSearchOr(q, matchingSetIds);

    const { data: cards, error } = await supabase
      .from('cards')
      .select(`id, name_kr, name_jp, name_en, rarity, card_sets ( set_code, name_kr )`)
      .in('set_id', searchSetIds)
      .or(cardFilter)
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
    const listCodes = SEARCH_SET_CODES as readonly string[];
    const sets = MOCK_SETS
      .filter(s => listCodes.includes(s.code) && matchesSearchQuery(s.name, q))
      .slice(0, 5)
      .map(s => ({ id: s.id, name: s.name, code: s.code }));

    const cards = MOCK_CARDS
      .filter(c => listCodes.includes(c.setCode) && isDisplayableRarity(c.rarity))
      .filter(c => matchesSearchQuery(c.name, q) || matchesSearchQuery(c.enName, q) || matchesSearchQuery(c.set, q))
      .slice(0, limit)
      .map(c => ({ id: c.id, name: c.name, rarity: c.rarity, set: c.set }));

    return NextResponse.json({ cards, sets });
  }
}
