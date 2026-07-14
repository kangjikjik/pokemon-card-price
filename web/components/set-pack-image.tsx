'use client';

import Image from 'next/image';
import { Package } from 'lucide-react';
import { cn } from '@/lib/utils';

/** 확장팩 한국판 팩/박스 */
export const SetPackImage = ({
  imageUrl,
  alt,
  colorClass = 'from-slate-600 to-slate-800',
  className,
  size = 'md',
}: {
  imageUrl?: string;
  alt: string;
  colorClass?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}) => {
  const sizeClass =
    size === 'sm' ? 'max-w-[100px]' : size === 'lg' ? 'max-w-[220px]' : 'max-w-[180px]';

  return (
    <div
      className={cn(
        'aspect-[5/7] w-full mx-auto bg-slate-950 relative overflow-hidden rounded-xl',
        sizeClass,
        className,
      )}
    >
      <div className={cn('absolute inset-0 bg-gradient-to-br opacity-15', colorClass)} />
      {imageUrl ? (
        <div className="relative w-full h-full p-1">
          <Image
            src={imageUrl}
            alt={alt}
            fill
            sizes="(max-width: 768px) 45vw, 220px"
            className="object-contain drop-shadow-lg relative z-10 scale-[1.08]"
            unoptimized
          />
        </div>
      ) : (
        <div className="relative z-10 w-full h-full flex items-center justify-center">
          <Package className="w-10 h-10 text-slate-400" />
        </div>
      )}
    </div>
  );
};
