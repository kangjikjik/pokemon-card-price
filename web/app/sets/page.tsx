import { Package } from 'lucide-react';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_SETS, type SetData } from '@/lib/data';
import { FEATURED_SET_CODES } from '@/lib/constants';
import { mapRawSet } from '@/lib/set-map';
import { SetsGrid } from '@/components/sets-grid';
import { ScrollFab } from '@/components/scroll-fab';

export const dynamic = 'force-dynamic';

async function getSets(): Promise<SetData[]> {
  try {
    const supabase = getSupabaseServer();
    const { data, error } = await supabase
      .from('card_sets')
      .select(`id, set_code, name_kr, name_jp, name_en, released_at, image_url, prices_box ( region, price_krw )`)
      .in('set_code', [...FEATURED_SET_CODES])
      .order('released_at', { ascending: false });

    if (error || !data || data.length === 0) throw new Error('no data');
    return data.map(raw => mapRawSet(raw));
  } catch {
    return MOCK_SETS.filter(s => (FEATURED_SET_CODES as readonly string[]).includes(s.code));
  }
}

export default async function SetsPage() {
  const sets = await getSets();

  return (
    <>
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <Package className="w-8 h-8 text-amber-500 mr-3" />
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white">확장팩 시세</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            총 <span className="font-semibold text-slate-700 dark:text-slate-200">{sets.length}</span>개
          </p>
        </div>

        <SetsGrid sets={sets} />
      </div>
      <ScrollFab />
    </>
  );
}
