'use client';

import Image from 'next/image';
import { Package } from 'lucide-react';
import { cn } from '@/lib/utils';

/** 확장팩·프로모팩 박스/팩 이미지 — 비율 통일, 잘림 방지 */
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
        'aspect-[3/4] w-full mx-auto bg-slate-950 relative overflow-hidden rounded-xl',
        sizeClass,
        className,
      )}
    >
      <div className={cn('absolute inset-0 bg-gradient-to-br opacity-15', colorClass)} />
      {imageUrl ? (
        <div className="absolute inset-0 flex items-center justify-center p-3 sm:p-4">
          <Image
            src={imageUrl}
            alt={alt}
            width={400}
            height={520}
            className="max-w-full max-h-full w-auto h-auto object-contain drop-shadow-lg relative z-10"
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
