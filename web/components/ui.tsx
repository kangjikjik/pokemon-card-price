'use client';

import Image from 'next/image';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { normalizeCardImageUrl } from '@/lib/card-image-url';
import { normalizeRarity } from '@/lib/rarity';

export const RarityBadge = ({ rarity }: { rarity: string }) => {
  const r = normalizeRarity(rarity);
  const getBadgeStyle = (label: string) => {
    switch (label) {
      case 'MUR': return 'bg-gradient-to-r from-rose-500 via-red-600 to-amber-500 text-white shadow-[0_0_10px_rgba(244,63,94,0.5)]';
      case 'MA': return 'bg-gradient-to-r from-amber-600 via-orange-600 to-red-700 text-white shadow-[0_0_10px_rgba(234,88,12,0.5)]';
      case 'BWR': return 'bg-gradient-to-r from-zinc-700 via-slate-300 to-zinc-900 text-white shadow-[0_0_10px_rgba(148,163,184,0.4)]';
      case 'FUR': return 'bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-600 text-white shadow-[0_0_10px_rgba(56,189,248,0.45)]';
      case 'PKR': return 'bg-gradient-to-r from-yellow-300 via-amber-400 to-yellow-500 text-slate-900 shadow-[0_0_8px_rgba(251,191,36,0.45)]';
      case 'SAR': return 'bg-gradient-to-r from-yellow-400 via-amber-500 to-yellow-600 text-slate-900 shadow-[0_0_10px_rgba(245,158,11,0.5)]';
      case 'UR': return 'bg-gradient-to-r from-amber-400 via-yellow-500 to-amber-600 text-slate-900 shadow-[0_0_8px_rgba(251,191,36,0.5)]';
      case 'HR': return 'bg-gradient-to-r from-pink-500 via-purple-500 to-cyan-400 text-white shadow-[0_0_10px_rgba(236,72,153,0.5)]';
      case 'SR': return 'bg-gradient-to-r from-slate-200 via-slate-300 to-slate-400 text-slate-900';
      case 'CSR': return 'bg-gradient-to-r from-indigo-400 via-violet-500 to-purple-500 text-white';
      case 'CHR': return 'bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-500 text-white';
      case 'AR': return 'bg-gradient-to-r from-teal-400 to-emerald-500 text-slate-900';
      case 'ACE': return 'bg-gradient-to-r from-fuchsia-500 to-pink-600 text-white';
      case 'RRR': return 'bg-gradient-to-r from-orange-500 to-red-500 text-white';
      case 'RR': return 'bg-gradient-to-r from-blue-500 to-cyan-600 text-white';
      case 'RM': return 'bg-gradient-to-r from-sky-200 via-blue-300 to-indigo-400 text-slate-900 shadow-[0_0_8px_rgba(96,165,250,0.45)]';
      case 'A': return 'bg-gradient-to-r from-red-500 via-yellow-400 to-blue-500 text-white';
      case 'K': return 'bg-gradient-to-r from-yellow-300 via-amber-400 to-yellow-500 text-slate-900';
      case 'PR': return 'bg-gradient-to-r from-violet-600 to-indigo-800 text-white';
      default: return 'bg-slate-700 text-slate-200';
    }
  };

  return (
    <span className={cn('px-2 py-0.5 rounded text-xs font-bold tracking-wider', getBadgeStyle(r))}>
      {r}
    </span>
  );
};

export const TrendBadge = ({ value }: { value: number }) => {
  const isUp = value > 0;
  const isDown = value < 0;
  return (
    <div className={cn('flex items-center text-sm font-medium', isUp ? 'text-emerald-400' : isDown ? 'text-rose-400' : 'text-slate-400')}>
      {isUp && <TrendingUp className="w-4 h-4 mr-1" />}
      {isDown && <TrendingDown className="w-4 h-4 mr-1" />}
      {!isUp && !isDown && <span className="w-4 h-4 mr-1 text-center">-</span>}
      {Math.abs(value).toFixed(1)}%
    </div>
  );
};

export const FlagKR = ({ className }: { className?: string }) => (
  <span className={cn('inline-flex items-center justify-center text-sm leading-none select-none', className)} title="한국판">🇰🇷</span>
);

export const FlagJP = ({ className }: { className?: string }) => (
  <span className={cn('inline-flex items-center justify-center text-sm leading-none select-none', className)} title="일본판">🇯🇵</span>
);

export const RegionLabel = ({
  region,
  suffix = '',
  className,
}: {
  region: 'KR' | 'JP';
  suffix?: string;
  className?: string;
}) => {
  const Flag = region === 'KR' ? FlagKR : FlagJP;
  const label = region === 'KR' ? '한국판' : '일본판';
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-sm leading-none', className)}>
      <Flag />
      <span>{label}{suffix}</span>
    </span>
  );
};

export const CardPlaceholder = ({ colorClass, className }: { colorClass: string; className?: string }) => (
  <div className={cn('w-full h-full rounded-lg bg-gradient-to-br shadow-inner flex items-center justify-center relative overflow-hidden', colorClass, className)}>
    <div className="absolute inset-0 opacity-20 mix-blend-overlay" style={{ backgroundImage: "url('https://www.transparenttextures.com/patterns/cubes.png')" }} />
    <div className="w-3/4 h-1/2 bg-black/20 backdrop-blur-sm rounded border border-white/20" />
  </div>
);

export const CardImage = ({
  imageUrl,
  altText,
  colorClass,
  className,
}: {
  imageUrl?: string;
  altText: string;
  colorClass: string;
  className?: string;
}) => {
  if (imageUrl) {
    return (
      <div className={cn('w-full h-full relative rounded-lg overflow-hidden', className)}>
        <Image
                src={normalizeCardImageUrl(imageUrl) ?? imageUrl}
          alt={altText}
          fill
          sizes="(max-width: 768px) 50vw, 25vw"
          className="object-contain drop-shadow-xl"
          unoptimized
        />
      </div>
    );
  }
  return <CardPlaceholder colorClass={colorClass} className={className} />;
};
