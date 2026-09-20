import { NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_SETS } from '@/lib/data';
import { FEATURED_SET_CODES } from '@/lib/constants';
import { mapRawSet } from '@/lib/set-map';
import { fetchRecentBoxPricesBySet } from '@/lib/fetch-recent-box-prices';

export async function GET() {
  try {
    const supabase = getSupabaseServer();

    const { data, error } = await supabase
      .from('card_sets')
      .select(`
        id, set_code, name_kr, name_jp, name_en, released_at, image_url
      `)
      .in('set_code', [...FEATURED_SET_CODES])
      .order('released_at', { ascending: false });

    if (error) throw error;
    if (!data || data.length === 0) throw new Error('No data');

    const boxMap = await fetchRecentBoxPricesBySet(supabase, data.map(d => d.id as number));
    return NextResponse.json({
      data: data.map(d => mapRawSet({ ...d, prices_box: boxMap.get(d.id as number) ?? [] })),
      source: 'db',
    });
  } catch {
    const mock = MOCK_SETS.filter(s => (FEATURED_SET_CODES as readonly string[]).includes(s.code));
    return NextResponse.json({ data: mock, source: 'mock' });
  }
}
