import { NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { CARDS_LIST_SET_CODES } from '@/lib/constants';
import { DISPLAY_RARITIES, RARITY_ALIASES } from '@/lib/rarity';

function rawRarities(code: string): string[] {
  const aliases = Object.entries(RARITY_ALIASES)
    .filter(([, value]) => value === code)
    .map(([key]) => key);
  return [...new Set([code, ...aliases])];
}

export async function GET() {
  try {
    const supabase = getSupabaseServer();

    const { data: featuredSets } = await supabase
      .from('card_sets')
      .select('id')
      .in('set_code', [...CARDS_LIST_SET_CODES]);

    const featuredSetIds = (featuredSets || []).map((s) => s.id);
    if (featuredSetIds.length === 0) throw new Error('No featured sets');

    const counts = new Map<string, number>();
    const results = await Promise.all(
      DISPLAY_RARITIES.map(async (code) => {
        const { count, error } = await supabase
          .from('cards')
          .select('id', { count: 'exact', head: true })
          .in('set_id', featuredSetIds)
          .in('rarity', rawRarities(code));
        if (error) throw error;
        return [code, count ?? 0] as const;
      }),
    );

    let total = 0;
    for (const [code, count] of results) {
      if (count <= 0) continue;
      counts.set(code, count);
      total += count;
    }

    return NextResponse.json(
      { total, byRarity: Object.fromEntries(counts), source: 'db' },
      { headers: { 'Cache-Control': 'public, s-maxage=600, stale-while-revalidate=600' } },
    );
  } catch {
    return NextResponse.json({ total: 0, byRarity: {}, source: 'mock' });
  }
}
