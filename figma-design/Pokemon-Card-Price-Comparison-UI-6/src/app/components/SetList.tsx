import React from 'react';
import { Link } from 'react-router-dom';
import { Package } from 'lucide-react';
import { MOCK_SETS, formatKRW } from '../data';
import { FlagKR, FlagJP } from './ui';

export const SetList = () => {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center mb-8">
        <Package className="w-8 h-8 text-amber-500 mr-3" />
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">확장팩 시세</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {MOCK_SETS.map(set => (
          <Link to={`/sets/${set.id}`} key={set.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden hover:border-amber-500/50 dark:hover:border-amber-500/50 transition-all group hover:-translate-y-1 shadow-sm hover:shadow-md">
            <div className={`h-32 w-full bg-gradient-to-r ${set.imageColor} relative flex items-center justify-center`}>
              <div className="absolute inset-0 bg-black/10 dark:bg-black/20 mix-blend-overlay"></div>
            </div>
            
            <div className="p-6">
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-1">{set.name}</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">{set.enName} · 발매일: {set.releaseDate}</p>

              <div className="space-y-3">
                <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <FlagKR />
                    <span className="text-slate-600 dark:text-slate-400 text-sm">한국판 박스</span>
                  </div>
                  <span className="text-slate-900 dark:text-white font-bold">{formatKRW(set.boxPriceKR)}</span>
                </div>
                <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <FlagJP />
                    <span className="text-slate-600 dark:text-slate-400 text-sm">일본판 박스</span>
                  </div>
                  <span className="text-slate-900 dark:text-white font-bold">{formatKRW(set.boxPriceJP)}</span>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};