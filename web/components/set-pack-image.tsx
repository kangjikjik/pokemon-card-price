'use client';

import Image from 'next/image';
import { Package } from 'lucide-react';
import { cn } from '@/lib/utils';

/** 확장팩·프로모팩 박스/팩 이미지 — 원본 전체가 보이도록 비율 유지 */
export const SetPackImage = ({
  imageUrl,
  alt,
  compact = false,
  className,
  size = 'md',
}: {
  imageUrl?: string;
  alt: string;
  compact?: boolean;
  colorClass?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}) => {
  const sizeClass =
    size === 'sm' ? 'max-w-[100px]' : size === 'lg' ? 'max-w-[220px]' : 'max-w-[180px]';

  return (
    <div
      className={cn(
        'aspect-[3/4] w-full mx-auto bg-black relative overflow-hidden rounded-xl',
        sizeClass,
        className,
      )}
    >
      {imageUrl ? (
        <div className="absolute inset-0 flex items-center justify-center p-3 sm:p-4">
          <Image
            src={imageUrl}
            alt={alt}
            width={400}
            height={520}
            className={cn(
              'max-w-full h-auto w-auto object-contain drop-shadow-lg relative z-10',
              compact ? 'max-h-[60%]' : 'max-h-full',
            )}
            unoptimized
          />
        </div>
      ) : (
        <div className="relative z-10 w-full h-full flex flex-col items-center justify-center gap-3 text-slate-500">
          <Package className="w-12 h-12 text-slate-400" />
          <span className="text-xs font-medium">기본 이미지</span>
        </div>
      )}
    </div>
  );
};
