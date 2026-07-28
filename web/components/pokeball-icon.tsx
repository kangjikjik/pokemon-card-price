import { cn } from '@/lib/utils';

/** Navbar·favicon·세트 아이콘 공통 몬스터볼 */
export function PokeballIcon({ className, size = 'md' }: { className?: string; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClass = size === 'sm' ? 'w-5 h-5' : size === 'lg' ? 'w-8 h-8' : 'w-6 h-6';

  return (
    <div
      className={cn(
        'rounded-full bg-gradient-to-br from-red-500 to-red-600 border-2 border-white dark:border-slate-900 flex items-center justify-center relative overflow-hidden shadow-[0_0_10px_rgba(239,68,68,0.45)]',
        sizeClass,
        className,
      )}
      aria-hidden
    >
      <div className="absolute top-1/2 left-0 w-full h-[2px] bg-white dark:bg-slate-900 -translate-y-1/2" />
      <div className="absolute top-1/2 left-1/2 w-[38%] h-[38%] bg-slate-900 dark:bg-white rounded-full border-2 border-white dark:border-slate-900 -translate-x-1/2 -translate-y-1/2 z-10" />
      <div className="w-full h-1/2 bg-slate-900 dark:bg-white absolute bottom-0" />
    </div>
  );
}
