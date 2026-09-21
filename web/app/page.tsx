import Link from 'next/link';
import { ChevronRight, Flame } from 'lucide-react';
import { SearchBox } from '@/components/search-box';
import { MOCK_CARDS, MOCK_SETS, formatKRW } from '@/lib/data';
import { formatYen } from '@/lib/set-msrp';
import { FEATURED_SET_CODES } from '@/lib/constants';
import { RarityBadge, TrendBadge, CardImage, RegionLabel } from '@/components/ui';
import { getHomePageData } from '@/lib/home-cards';

export const dynamic = 'force-dynamic';

async function getHomeData() {
  try {
    return await getHomePageData();
  } catch (err) {
    console.error('[home] DB error:', err);
    const featuredCodes = FEATURED_SET_CODES as readonly string[];
    const cards = MOCK_CARDS.filter(c => featuredCodes.includes(c.setCode));
    return {
      highlight: cards[0],
      trending: cards.slice(1, 5),
      sets: MOCK_SETS.filter(s => featuredCodes.includes(s.code)),
    };
  }
}

export default async function HomePage() {
  const { highlight: highlightCard, trending: topCards, sets } = await getHomeData();

  if (!highlightCard) {
    return null;
  }

  return (
    <div className="space-y-12 pb-12">
      {/* Hero Section */}
      <section className="relative -mt-0 pt-20 pb-16 px-4 md:px-8 bg-gradient-to-b from-slate-100 via-slate-50 to-slate-100 dark:from-indigo-950 dark:via-slate-900 dark:to-slate-950 transition-colors duration-300">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-red-600 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] animate-pulse" />
          <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-amber-500 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] animate-pulse" style={{ animationDelay: '1s' }} />
        </div>
        <div className="max-w-6xl mx-auto relative z-10 flex flex-col items-center text-center">
          <h1 className="text-4xl md:text-6xl font-extrabold text-slate-900 dark:text-white mb-8 tracking-tight">
            포켓몬 카드 시세의{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-amber-500">모든 것</span>
          </h1>
          <div className="w-full max-w-2xl relative z-30">
            <SearchBox
              inputClassName="py-4 text-base rounded-full shadow-xl"
              placeholder="카드 이름 또는 세트명으로 검색..."
            />
          </div>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-4 space-y-12">
        {/* Highlight Section */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center">
              <Flame className="w-6 h-6 text-orange-500 mr-2" /> 주간 핫 카드
            </h2>
          </div>
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row gap-8 items-center relative overflow-hidden group hover:border-slate-300 dark:hover:border-slate-700 shadow-sm transition-colors">
            <div className="w-full md:w-1/3 aspect-[63/88] max-w-[280px] shrink-0 transform group-hover:scale-105 transition-transform duration-500">
              <CardImage
                imageUrl={highlightCard.imageUrl}
                altText={highlightCard.name}
                colorClass={highlightCard.imageColor}
                className="shadow-2xl shadow-orange-900/20"
              />
            </div>
            <div className="flex-1 space-y-6 z-10 w-full">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <RarityBadge rarity={highlightCard.rarity} />
                  <span className="text-slate-500 dark:text-slate-400 text-sm">{highlightCard.set}</span>
                </div>
                <h3 className="text-4xl font-bold text-slate-900 dark:text-white mb-1">{highlightCard.name}</h3>
                <p className="text-slate-500 dark:text-slate-400">{highlightCard.enName}</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-slate-50 dark:bg-slate-950/50 rounded-xl p-5 border border-slate-100 dark:border-slate-800/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-600 dark:text-slate-400"><RegionLabel region="KR" suffix=" 시세" /></span>
                    {highlightCard.trendKR !== 0 && <TrendBadge value={highlightCard.trendKR} />}
                  </div>
                  <div className="text-3xl font-bold text-slate-900 dark:text-white">
                    {highlightCard.priceKR > 0 ? formatKRW(highlightCard.priceKR) : '미등록'}
                  </div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-950/50 rounded-xl p-5 border border-slate-100 dark:border-slate-800/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-600 dark:text-slate-400"><RegionLabel region="JP" suffix=" 시세" /></span>
                    {highlightCard.trendJP !== 0 && <TrendBadge value={highlightCard.trendJP} />}
                  </div>
                  <div className="text-3xl font-bold text-slate-900 dark:text-white">
                    {highlightCard.priceJP > 0 ? formatKRW(highlightCard.priceJP) : '미등록'}
                  </div>
                </div>
              </div>
              <Link href={`/cards/${highlightCard.id}`} className="inline-flex items-center justify-center bg-slate-900 text-white dark:bg-white dark:text-slate-950 px-6 py-3 rounded-lg font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors w-full sm:w-auto shadow-sm">
                상세 분석 보기 <ChevronRight className="w-4 h-4 ml-2" />
              </Link>
            </div>
          </div>
        </section>

        {/* Popular Cards Grid */}
        {topCards.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white">인기 급상승 카드</h2>
              <Link href="/cards?sort=popular" className="text-amber-600 dark:text-amber-500 hover:text-amber-500 dark:hover:text-amber-400 text-sm flex items-center font-medium">
                전체보기 <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
              {topCards.map(card => (
                <Link href={`/cards/${card.id}`} key={card.id} className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:border-amber-500/50 transition-colors shadow-sm hover:shadow-md">
                  <div className="aspect-[63/88] p-4 bg-slate-50 dark:bg-slate-950">
                    <div className="w-full h-full relative group-hover:-translate-y-2 group-hover:scale-105 transition-all duration-300">
                      <CardImage imageUrl={card.imageUrl} altText={card.name} colorClass={card.imageColor} />
                    </div>
                  </div>
                  <div className="p-4 flex-1 flex flex-col">
                    <div className="flex justify-between items-start mb-2">
                      <RarityBadge rarity={card.rarity} />
                    </div>
                    <h4 className="text-slate-900 dark:text-white font-semibold truncate mb-3">{card.name}</h4>
                    <div className="mt-auto space-y-2">
                      <div className="flex justify-between items-center">
                        <RegionLabel region="KR" />
                        <span className="text-slate-700 dark:text-slate-300 text-sm font-medium">
                          {card.priceKR > 0 ? formatKRW(card.priceKR) : '미등록'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <RegionLabel region="JP" />
                        <span className="text-slate-700 dark:text-slate-300 text-sm font-medium">
                          {card.priceJP > 0 ? formatKRW(card.priceJP) : '미등록'}
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Top Sets */}
        {sets.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white">주요 세트</h2>
              <Link href="/sets" className="text-amber-600 dark:text-amber-500 hover:text-amber-500 dark:hover:text-amber-400 text-sm flex items-center font-medium">
                전체보기 <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {sets.map(set => (
                <Link href={`/sets/${set.id}`} key={set.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-sm">
                  <h4 className="text-slate-900 dark:text-white font-semibold truncate mb-3">{set.name}</h4>
                  <div className="text-xs flex flex-col gap-2">
                    <span className="flex items-center gap-2 flex-wrap">
                      <RegionLabel region="KR" />
                      {set.boxPriceKR > 0 ? (
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{formatKRW(set.boxPriceKR)}</span>
                      ) : (
                        <span className="text-slate-500 dark:text-slate-400">시세 미등록</span>
                      )}
                      {set.msrpBoxKR > 0 && (
                        <span className="text-slate-400">· 발매가 {formatKRW(set.msrpBoxKR)}</span>
                      )}
                    </span>
                    <span className="flex items-center gap-2 flex-wrap">
                      <RegionLabel region="JP" />
                      {set.boxPriceJP > 0 ? (
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{formatKRW(set.boxPriceJP)}</span>
                      ) : (
                        <span className="text-slate-500 dark:text-slate-400">시세 미등록</span>
                      )}
                      {set.msrpBoxJP > 0 && (
                        <span className="text-slate-400">· 발매가 {formatYen(set.msrpBoxJP)}</span>
                      )}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
