'use client';

import { useRouter } from 'next/navigation';
import type { ReactNode, KeyboardEvent } from 'react';
import { saveScrollPosition } from '@/lib/scroll-restore';

type Props = {
  href: string;
  className?: string;
  children: ReactNode;
};

export function ClickableTableRow({ href, className = '', children }: Props) {
  const router = useRouter();

  const navigate = () => {
    saveScrollPosition();
    router.push(href);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTableRowElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      navigate();
    }
  };

  return (
    <tr
      onClick={navigate}
      onKeyDown={onKeyDown}
      tabIndex={0}
      role="link"
      className={`cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50 ${className}`}
    >
      {children}
    </tr>
  );
}
