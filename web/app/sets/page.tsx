import { Package } from 'lucide-react';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_SETS, type SetData } from '@/lib/data';
import {
  EXPANSION_SET_CODES,
  FEATURED_SET_CODES,
  SETS_PAGE_EXTRA_CODES,
  isPromoPageSetCode,
  isSpecialSetCode,
} from '@/lib/constants';
import { mapRawSet } from '@/lib/set-map';
import { SetsTabs } from '@/components/sets-tabs';
import { ScrollFab } from '@/components/scroll-fab';

export const dynamic = 'force-dynamic';

async function getSets(): Promise<SetData[]> {
  try {
    const supabase = getSupabaseServer();
    const { data, error } = await supabase
      .from('card_sets')
      .select(`id, set_code, name_kr, name_jp, name_en, released_at, image_url, prices_box ( region, price_krw )`)
      .in('set_code', [...FEATURED_SET_CODES, ...SETS_PAGE_EXTRA_CODES])
      .order('released_at', { ascending: false });

    if (error || !data || data.length === 0) throw new Error('no data');
    return data.map((raw) => mapRawSet(raw));
  } catch {
    return MOCK_SETS.filter((s) => (FEATURED_SET_CODES as readonly string[]).includes(s.code));
  }
}

function splitSets(sets: SetData[]) {
  const expansionSets = sets.filter((s) =>
    (EXPANSION_SET_CODES as readonly string[]).includes(s.code),
  );
  const specialSets = sets.filter((s) => isSpecialSetCode(s.code));
  const promoSets = sets.filter((s) => isPromoPageSetCode(s.code));
  return { expansionSets, specialSets, promoSets };
}

export default async function SetsPage() {
  const { expansionSets, specialSets, promoSets } = splitSets(await getSets());
  const totalCount = expansionSets.length + specialSets.length + promoSets.length;

  return (
    <>
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <Package className="w-8 h-8 text-amber-500 mr-3" />
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white">세트 시세</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            총 <span className="font-semibold text-slate-700 dark:text-slate-200">{totalCount}</span>개
          </p>
        </div>

        <SetsTabs expansionSets={expansionSets} specialSets={specialSets} promoSets={promoSets} />
      </div>
      <ScrollFab />
    </>
  );
}
