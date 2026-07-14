'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BOARDS, type BoardSlug } from '@/lib/community';

export function CommunityBoardNav({ active }: { active?: BoardSlug }) {
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap gap-2">
      {Object.values(BOARDS).map(board => {
        const href = `/community/${board.slug}`;
        const isActive = active === board.slug || pathname === href || pathname.startsWith(`${href}/`);
        const Icon = board.icon;
        return (
          <Link
            key={board.slug}
            href={href}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all border ${
              isActive
                ? 'bg-amber-500 text-white border-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.35)]'
                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-amber-400'
            }`}
          >
            <Icon className="w-4 h-4" />
            {board.label}
          </Link>
        );
      })}
    </div>
  );
}
