import { NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { CARDS_LIST_SET_CODES } from '@/lib/constants';
import { isDisplayableRarity, normalizeRarity } from '@/lib/rarity';

export async function GET() {
  try {
    const supabase = getSupabaseServer();

    const { data: featuredSets } = await supabase
      .from('card_sets')
      .select('id')
      .in('set_code', [...CARDS_LIST_SET_CODES]);

    const featuredSetIds = (featuredSets || []).map((s) => s.id);
    if (featuredSetIds.length === 0) throw new Error('No featured sets');

    const BATCH = 1000;
    const counts = new Map<string, number>();
    let total = 0;
    let offset = 0;

    while (true) {
      const { data, error } = await supabase
        .from('cards')
        .select('rarity')
        .in('set_id', featuredSetIds)
        .order('id', { ascending: true })
        .range(offset, offset + BATCH - 1);

      if (error) throw error;
      if (!data || data.length === 0) break;

      for (const row of data) {
        const rarity = normalizeRarity((row.rarity as string) || '');
        if (!isDisplayableRarity(rarity)) continue;
        total += 1;
        counts.set(rarity, (counts.get(rarity) || 0) + 1);
      }

      if (data.length < BATCH) break;
      offset += BATCH;
    }

    return NextResponse.json(
      { total, byRarity: Object.fromEntries(counts), source: 'db' },
      { headers: { 'Cache-Control': 'no-store' } },
    );
  } catch {
    return NextResponse.json({ total: 0, byRarity: {}, source: 'mock' });
  }
}
