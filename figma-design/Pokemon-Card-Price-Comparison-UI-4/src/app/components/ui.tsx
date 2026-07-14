import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { TrendingUp, TrendingDown } from 'lucide-react';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const RarityBadge = ({ rarity }: { rarity: string }) => {
  const getBadgeStyle = (r: string) => {
    switch (r) {
      case 'UR': return 'bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 text-white shadow-[0_0_10px_rgba(236,72,153,0.5)]';
      case 'SAR': return 'bg-gradient-to-r from-yellow-400 via-amber-500 to-yellow-600 text-slate-900 shadow-[0_0_10px_rgba(245,158,11,0.5)]';
      case 'SR': return 'bg-gradient-to-r from-slate-200 via-slate-300 to-slate-400 text-slate-900';
      case 'SA': return 'bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white';
      case 'AR': return 'bg-gradient-to-r from-teal-400 to-emerald-500 text-slate-900';
      default: return 'bg-slate-700 text-slate-200';
    }
  };

  return (
    <span className={cn("px-2 py-0.5 rounded text-xs font-bold tracking-wider", getBadgeStyle(rarity))}>
      {rarity}
    </span>
  );
};

export const TrendBadge = ({ value }: { value: number }) => {
  const isUp = value > 0;
  const isDown = value < 0;
  return (
    <div className={cn("flex items-center text-sm font-medium", isUp ? "text-emerald-400" : isDown ? "text-rose-400" : "text-slate-400")}>
      {isUp && <TrendingUp className="w-4 h-4 mr-1" />}
      {isDown && <TrendingDown className="w-4 h-4 mr-1" />}
      {!isUp && !isDown && <span className="w-4 h-4 mr-1 text-center">-</span>}
      {Math.abs(value).toFixed(1)}%
    </div>
  );
};

export const FlagKR = () => (
  <span className="text-xl leading-none drop-shadow-sm" title="한국판">
    🇰🇷
  </span>
);

export const FlagJP = () => (
  <span className="text-xl leading-none drop-shadow-sm" title="일본판">
    🇯🇵
  </span>
);

export const CardPlaceholder = ({ colorClass, className }: { colorClass: string, className?: string }) => (
  <div className={cn("w-full h-full rounded-lg bg-gradient-to-br shadow-inner flex items-center justify-center relative overflow-hidden", colorClass, className)}>
    <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-20 mix-blend-overlay"></div>
    <div className="w-3/4 h-1/2 bg-black/20 backdrop-blur-sm rounded border border-white/20"></div>
  </div>
);
