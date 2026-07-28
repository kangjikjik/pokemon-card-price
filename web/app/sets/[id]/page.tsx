import Link from 'next/link';
import { ChevronLeft } from 'lucide-react';
import { notFound } from 'next/navigation';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_SETS, MOCK_CARDS } from '@/lib/data';
import { FEATURED_SET_CODES, isViewableSetCode } from '@/lib/constants';
import { mapRawSet } from '@/lib/set-map';
import { SetPackImage } from '@/components/set-pack-image';
import { SetBoxPriceRows } from '@/components/set-box-price';
import { ScrollFab } from '@/components/scroll-fab';
import { ScrollRestore } from '@/components/scroll-restore';
import { compareCardsByRarity, isDisplayableRarity } from '@/lib/rarity';
import { SetCardsPriceTable } from '@/components/set-cards-price-table';

export default async function SetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const numericId = parseInt(id);

  let set = mapRawSet({
    id: id,
    set_code: '',
    name_kr: '',
    name_en: '',
    released_at: '',
    image_url: '',
    prices_box: [],
  });
  let cards: { id: number; name_kr: string; name_jp: string; name_en: string; rarity: string; card_number: string; image_color: string; prices_kr: { price_krw: number; fetched_at?: string }[]; prices_jp: { price_krw: number; fetched_at?: string }[] }[] = [];
  let usedMock = false;

  try {
    if (isNaN(numericId)) throw new Error('non-numeric');
    const supabase = getSupabaseServer();

    const [setResult, cardsResult] = await Promise.all([
      supabase
        .from('card_sets')
        .select(`id, set_code, name_kr, name_jp, name_en, released_at, image_url, prices_box ( region, price_krw, fetched_at )`)
        .eq('id', numericId)
        .single(),
      supabase
        .from('cards')
        .select(`id, name_kr, name_jp, name_en, rarity, rarity_rank, image_url, image_color, card_number, prices_kr ( price_krw, fetched_at ), prices_jp ( price_krw, fetched_at )`)
        .eq('set_id', numericId)
        .order('rarity_rank', { ascending: false })
        .order('card_number', { ascending: true }),
    ]);

    if (setResult.error) throw setResult.error;
    if (!setResult.data) throw new Error('not found');
    if (!isViewableSetCode(setResult.data.set_code)) notFound();

    const raw = setResult.data;
    set = mapRawSet(raw);
    cards = (cardsResult.data || [])
      .filter(c => isDisplayableRarity(c.rarity))
      .sort((a, b) => compareCardsByRarity(
        { rarity: a.rarity, setCode: set.code, number: a.card_number, name: a.name_kr || a.name_jp || a.name_en, imageUrl: (a as { image_url?: string }).image_url },
        { rarity: b.rarity, setCode: set.code, number: b.card_number, name: b.name_kr || b.name_jp || b.name_en, imageUrl: (b as { image_url?: string }).image_url },
      )) as typeof cards;
  } catch {
    usedMock = true;
    const featuredCodes = FEATURED_SET_CODES as readonly string[];
    const mockSet = MOCK_SETS.find(s => s.id === id && featuredCodes.includes(s.code));
    if (!mockSet) notFound();
    set = mockSet;
  }

  const mockCards = usedMock ? MOCK_CARDS.filter(c => c.set === set.name) : [];

  const tableCards = usedMock
    ? mockCards.map(c => ({
        id: c.id,
        name_kr: c.name,
        name_jp: '',
        name_en: c.enName,
        rarity: c.rarity,
        card_number: c.number,
        prices_kr: c.priceKR > 0 ? [{ price_krw: c.priceKR }] : [],
        prices_jp: c.priceJP > 0 ? [{ price_krw: c.priceJP }] : [],
      }))
    : cards;

  return (
    <>
    <ScrollRestore />
    <div className="max-w-6xl mx-auto px-4 py-8">
      <Link href="/sets" className="inline-flex items-center text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white mb-6 transition-colors">
        <ChevronLeft className="w-4 h-4 mr-1" /> 목록으로 돌아가기
      </Link>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden mb-8 flex flex-col md:flex-row shadow-sm">
        <div className="w-full md:w-44 shrink-0 p-4 md:p-6 flex items-center justify-center">
          <SetPackImage imageUrl={set.imageUrl} alt={set.name} colorClass={set.imageColor} size="lg" />
        </div>
        <div className="p-6 md:p-8 flex-1 flex flex-col justify-center">
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-2">{set.name}</h1>
          <p className="text-slate-500 dark:text-slate-400 mb-6">{set.enName} · 발매일: {set.releaseDate}</p>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <SetBoxPriceRows region="KR" marketPrice={set.boxPriceKR} msrpBox={set.msrpBoxKR} msrpPack={set.msrpPackKR} boxLabel="미개봉 박스" />
            </div>
            <div className="flex-1">
              <SetBoxPriceRows region="JP" marketPrice={set.boxPriceJP} msrpBox={set.msrpBoxJP} msrpPack={set.msrpPackJP} boxLabel="미개봉 박스" />
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">수록 카드</h2>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <SetCardsPriceTable cards={tableCards} />
        </div>
      </div>
    </div>
    <ScrollFab />
    </>
  );
}
