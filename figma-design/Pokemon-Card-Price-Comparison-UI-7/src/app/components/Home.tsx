import React from 'react';
import { Link } from 'react-router-dom';
import { Search, ChevronRight, Flame } from 'lucide-react';
import { MOCK_CARDS, MOCK_SETS, formatKRW } from '../data';
import { RarityBadge, TrendBadge, CardPlaceholder, FlagKR, FlagJP, cn } from './ui';

export const Home = () => {
  const highlightCard = MOCK_CARDS[0];
  const topCards = MOCK_CARDS.slice(1, 5);

  return (
    <div className="space-y-12 pb-12">
      {/* Hero Section */}
      <section className="relative -mt-8 pt-20 pb-16 px-4 md:px-8 bg-gradient-to-b from-slate-100 via-slate-50 to-slate-100 dark:from-indigo-950 dark:via-slate-900 dark:to-slate-950 overflow-hidden transition-colors duration-300">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-full opacity-10 dark:opacity-30 pointer-events-none">
           <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-red-600 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] animate-pulse"></div>
           <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-amber-500 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] animate-pulse delay-1000"></div>
        </div>

        <div className="max-w-6xl mx-auto relative z-10 flex flex-col items-center text-center">
          <h1 className="text-4xl md:text-6xl font-extrabold text-slate-900 dark:text-white mb-8 tracking-tight">
            포켓몬 카드 시세의 <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-amber-500">모든 것</span>
          </h1>

          <div className="w-full max-w-2xl relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-slate-400" />
            </div>
            <input 
              type="text" 
              placeholder="카드 이름 또는 세트명으로 검색..." 
              className="w-full bg-white/90 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 rounded-full py-4 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent backdrop-blur-sm shadow-xl transition-colors"
            />
          </div>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-4 space-y-12">
        
        {/* Highlight Section */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center">
              <Flame className="w-6 h-6 text-orange-500 mr-2" /> 주간 핫 리포트
            </h2>
          </div>
          
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row gap-8 items-center relative overflow-hidden group hover:border-slate-300 dark:hover:border-slate-700 shadow-sm transition-colors">
            <div className="w-full md:w-1/3 aspect-[63/88] max-w-[280px] shrink-0 transform group-hover:scale-105 transition-transform duration-500">
              <CardPlaceholder colorClass={highlightCard.imageColor} className="shadow-2xl shadow-orange-900/20" />
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
                    <span className="text-slate-600 dark:text-slate-400 flex items-center gap-2"><FlagKR /> 한국판 시세</span>
                    <TrendBadge value={highlightCard.trendKR} />
                  </div>
                  <div className="text-3xl font-bold text-slate-900 dark:text-white">{formatKRW(highlightCard.priceKR)}</div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-950/50 rounded-xl p-5 border border-slate-100 dark:border-slate-800/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-600 dark:text-slate-400 flex items-center gap-2"><FlagJP /> 일본판 시세</span>
                    <TrendBadge value={highlightCard.trendJP} />
                  </div>
                  <div className="text-3xl font-bold text-slate-900 dark:text-white">{formatKRW(highlightCard.priceJP)}</div>
                </div>
              </div>

              <Link to={`/cards/${highlightCard.id}`} className="inline-flex items-center justify-center bg-slate-900 text-white dark:bg-white dark:text-slate-950 px-6 py-3 rounded-lg font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors w-full sm:w-auto shadow-sm">
                상세 분석 보기 <ChevronRight className="w-4 h-4 ml-2" />
              </Link>
            </div>
          </div>
        </section>

        {/* Popular Cards Grid */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">인기 급상승 카드</h2>
            <Link to="/cards" className="text-amber-600 dark:text-amber-500 hover:text-amber-500 dark:hover:text-amber-400 text-sm flex items-center font-medium">
              전체보기 <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
            {topCards.map(card => (
              <Link to={`/cards/${card.id}`} key={card.id} className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:border-amber-500/50 transition-colors shadow-sm hover:shadow-md">
                <div className="aspect-[63/88] p-4 bg-slate-50 dark:bg-slate-950">
                  <div className="w-full h-full relative group-hover:-translate-y-2 group-hover:scale-105 transition-all duration-300">
                     <CardPlaceholder colorClass={card.imageColor} />
                  </div>
                </div>
                <div className="p-4 flex-1 flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <RarityBadge rarity={card.rarity} />
                  </div>
                  <h4 className="text-slate-900 dark:text-white font-semibold truncate mb-3">{card.name}</h4>
                  <div className="mt-auto space-y-2">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-1"><FlagKR /></div>
                      <span className="text-slate-700 dark:text-slate-300 text-sm font-medium">{formatKRW(card.priceKR)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-1"><FlagJP /></div>
                      <span className="text-slate-700 dark:text-slate-300 text-sm font-medium">{formatKRW(card.priceJP)}</span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Top Sets */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">주요 확장팩</h2>
            <Link to="/sets" className="text-amber-600 dark:text-amber-500 hover:text-amber-500 dark:hover:text-amber-400 text-sm flex items-center font-medium">
              전체보기 <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {MOCK_SETS.map(set => (
              <Link to={`/sets/${set.id}`} key={set.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex items-center hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-sm">
                <div className={cn("w-16 h-16 rounded shadow-inner shrink-0 mr-4 flex items-center justify-center", set.imageColor)}>
                  <span className="text-white/50 text-xs font-bold rotate-[-15deg] mix-blend-overlay">BOX</span>
                </div>
                <div className="overflow-hidden">
                  <h4 className="text-slate-900 dark:text-white font-medium truncate mb-1">{set.name}</h4>
                  <div className="text-xs text-slate-500 dark:text-slate-400 flex flex-col gap-1">
                    <span className="flex items-center justify-between gap-2"><span className="flex items-center gap-1"><FlagKR /></span> {formatKRW(set.boxPriceKR)}</span>
                    <span className="flex items-center justify-between gap-2"><span className="flex items-center gap-1"><FlagJP /></span> {formatKRW(set.boxPriceJP)}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>

      </div>
    </div>
  );
};