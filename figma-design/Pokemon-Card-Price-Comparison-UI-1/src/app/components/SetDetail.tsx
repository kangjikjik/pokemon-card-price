import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ChevronLeft, Package } from 'lucide-react';
import { MOCK_SETS, MOCK_CARDS, formatKRW } from '../data';
import { RarityBadge, FlagKR, FlagJP } from './ui';

export const SetDetail = () => {
  const { id } = useParams();
  const set = MOCK_SETS.find(s => s.id === id) || MOCK_SETS[0];
  const setCards = MOCK_CARDS.filter(c => c.set === set.name);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <Link to="/sets" className="inline-flex items-center text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white mb-6 transition-colors">
        <ChevronLeft className="w-4 h-4 mr-1" /> 목록으로 돌아가기
      </Link>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden mb-8 flex flex-col md:flex-row shadow-sm">
        <div className={`w-full md:w-64 h-48 md:h-auto bg-gradient-to-br ${set.imageColor} flex items-center justify-center p-8 relative`}>
          <div className="absolute inset-0 bg-black/10 dark:bg-black/20 mix-blend-overlay"></div>
          <Package className="w-24 h-24 text-white/70 dark:text-white/50 relative z-10" />
        </div>
        
        <div className="p-6 md:p-8 flex-1 flex flex-col justify-center">
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-2">{set.name}</h1>
          <p className="text-slate-500 dark:text-slate-400 mb-6">{set.enName} · 발매일: {set.releaseDate}</p>

          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 bg-slate-50 dark:bg-slate-950 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2 mb-1">
                <FlagKR />
                <span className="text-slate-600 dark:text-slate-400 text-sm">한국판 미개봉 박스</span>
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-white">{formatKRW(set.boxPriceKR)}</div>
            </div>
            <div className="flex-1 bg-slate-50 dark:bg-slate-950 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2 mb-1">
                <FlagJP />
                <span className="text-slate-600 dark:text-slate-400 text-sm">일본판 미개봉 박스</span>
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-white">{formatKRW(set.boxPriceJP)}</div>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">주요 수록 카드</h2>
        
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-sm">
                  <th className="p-4 font-medium">카드명</th>
                  <th className="p-4 font-medium">레어도</th>
                  <th className="p-4 font-medium text-right"><div className="flex items-center justify-end gap-2"><FlagKR /> 한국판</div></th>
                  <th className="p-4 font-medium text-right"><div className="flex items-center justify-end gap-2"><FlagJP /> 일본판</div></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {setCards.map(card => (
                  <tr key={card.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group">
                    <td className="p-4">
                      <Link to={`/cards/${card.id}`} className="font-bold text-slate-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                        {card.name}
                      </Link>
                    </td>
                    <td className="p-4"><RarityBadge rarity={card.rarity} /></td>
                    <td className="p-4 text-right font-medium text-slate-900 dark:text-white">{formatKRW(card.priceKR)}</td>
                    <td className="p-4 text-right font-medium text-slate-900 dark:text-white">{formatKRW(card.priceJP)}</td>
                  </tr>
                ))}
                {setCards.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-slate-500">
                      등록된 카드가 없습니다.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};