import { NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_SETS } from '@/lib/data';
import { FEATURED_SET_CODES } from '@/lib/constants';
import { mapRawSet } from '@/lib/set-map';

export async function GET() {
  try {
    const supabase = getSupabaseServer();

    const { data, error } = await supabase
      .from('card_sets')
      .select(`
        id, set_code, name_kr, name_jp, name_en, released_at, image_url,
        prices_box ( region, price_krw, fetched_at )
      `)
      .in('set_code', [...FEATURED_SET_CODES])
      .order('released_at', { ascending: false });

    if (error) throw error;
    if (!data || data.length === 0) throw new Error('No data');

    return NextResponse.json({ data: data.map(d => mapRawSet(d)), source: 'db' });
  } catch {
    const mock = MOCK_SETS.filter(s => (FEATURED_SET_CODES as readonly string[]).includes(s.code));
    return NextResponse.json({ data: mock, source: 'mock' });
  }
}
