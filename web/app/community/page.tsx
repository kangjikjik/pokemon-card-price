import Link from 'next/link';
import { Users } from 'lucide-react';
import { BOARDS } from '@/lib/community';
import { CommunityBoardNav } from '@/components/community-board-nav';

export default function CommunityPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-2">
        <Users className="w-8 h-8 text-amber-500" />
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">커뮤니티</h1>
      </div>
      <p className="text-slate-500 dark:text-slate-400 mb-8">
        자유롭게 소통하고, 질문하고, 꿀팁을 공유하고, 서비스 개선을 요청해 보세요.
      </p>

      <div className="mb-8">
        <CommunityBoardNav />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.values(BOARDS).map(board => {
          const Icon = board.icon;
          return (
            <Link
              key={board.slug}
              href={`/community/${board.slug}`}
              className="group rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 hover:border-amber-400 dark:hover:border-amber-500 transition-all shadow-sm hover:shadow-md"
            >
              <div
                className={`w-12 h-12 rounded-xl bg-gradient-to-br ${board.accent} flex items-center justify-center mb-4 shadow-lg`}
              >
                <Icon className="w-6 h-6 text-white" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                {board.label}
              </h2>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                {board.description}
              </p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
