import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Filter, ArrowUpDown, TrendingUp } from 'lucide-react';
import { MOCK_CARDS, formatKRW } from '../data';
import { RarityBadge, CardPlaceholder, FlagKR, FlagJP } from './ui';

export const CardList = () => {
  const [activeRarity, setActiveRarity] = useState('All');
  const [sortBy, setSortBy] = useState<'price' | 'popular'>('price');
  const rarities = ['All', 'SAR', 'UR', 'SA', 'AR', 'SR'];

  let filteredCards = activeRarity === 'All' 
    ? [...MOCK_CARDS] 
    : MOCK_CARDS.filter(c => c.rarity === activeRarity);

  filteredCards.sort((a, b) => {
    if (sortBy === 'price') {
      return b.priceKR - a.priceKR;
    } else {
      return b.trendKR - a.trendKR; // Using trendKR as popularity metric
    }
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col md:flex-row gap-8">
      
      {/* Sidebar Filters */}
      <aside className="w-full md:w-64 shrink-0 space-y-6">
        <div>
          <h3 className="text-slate-900 dark:text-white font-bold mb-4 flex items-center">
            <Filter className="w-4 h-4 mr-2" /> 필터
          </h3>
          
          <div className="space-y-4">
            <div>
              <label className="text-slate-500 dark:text-slate-400 text-sm mb-2 block">레어도</label>
              <div className="flex flex-wrap gap-2">
                {rarities.map(r => (
                  <button 
                    key={r}
                    onClick={() => setActiveRarity(r)}
                    className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                      activeRarity === r 
                        ? 'bg-amber-500 text-white dark:text-slate-900 shadow-sm' 
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Grid */}
      <div className="flex-1">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">모든 카드 ({filteredCards.length})</h2>
          <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
            <button 
              onClick={() => setSortBy('price')}
              className={`flex items-center px-3 py-1.5 rounded text-sm font-medium transition-colors ${sortBy === 'price' ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
            >
              <ArrowUpDown className="w-4 h-4 mr-1" /> 가격순
            </button>
            <button 
              onClick={() => setSortBy('popular')}
              className={`flex items-center px-3 py-1.5 rounded text-sm font-medium transition-colors ${sortBy === 'popular' ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
            >
              <TrendingUp className="w-4 h-4 mr-1" /> 인기순
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6">
          {filteredCards.map(card => (
            <Link to={`/cards/${card.id}`} key={card.id} className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:border-amber-500/50 dark:hover:border-amber-500/50 transition-colors shadow-sm hover:shadow-md">
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
                  <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-950/50 p-1.5 rounded">
                    <FlagKR />
                    <span className="text-slate-700 dark:text-slate-300 text-sm font-medium">{formatKRW(card.priceKR)}</span>
                  </div>
                  <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-950/50 p-1.5 rounded">
                    <FlagJP />
                    <span className="text-slate-700 dark:text-slate-300 text-sm font-medium">{formatKRW(card.priceJP)}</span>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};
