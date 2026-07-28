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
import { PokeballIcon } from '@/components/pokeball-icon';

export const dynamic = 'force-dynamic';

async function getSets(): Promise<SetData[]> {
  try {
    const supabase = getSupabaseServer();
    const { data, error } = await supabase
      .from('card_sets')
      .select(`id, set_code, name_kr, name_jp, name_en, released_at, image_url, prices_box ( region, price_krw, fetched_at )`)
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
  const commemorativeSets = sets
    .filter((s) => isSpecialSetCode(s.code) || isPromoPageSetCode(s.code))
    .sort((a, b) => (b.releaseDate || '').localeCompare(a.releaseDate || ''));
  return { expansionSets, commemorativeSets };
}

export default async function SetsPage() {
  const { expansionSets, commemorativeSets } = splitSets(await getSets());
  const totalCount = expansionSets.length + commemorativeSets.length;

  return (
    <>
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <PokeballIcon size="lg" className="mr-3 shrink-0" />
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white">세트 시세</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            총 <span className="font-semibold text-slate-700 dark:text-slate-200">{totalCount}</span>개
          </p>
        </div>

        <SetsTabs expansionSets={expansionSets} commemorativeSets={commemorativeSets} />
      </div>
      <ScrollFab />
    </>
  );
}
