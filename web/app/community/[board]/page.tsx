import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import { getSupabaseServer } from '@/lib/supabase';
import { BOARDS, isBoardSlug, POST_SELECT_FIELDS, type BoardSlug, type CommunityPost } from '@/lib/community';
import { CommunityBoardNav } from '@/components/community-board-nav';
import { PostList } from '@/components/post-list';
import { WritePostForm } from '@/components/write-post-form';

export const dynamic = 'force-dynamic';

type Props = { params: Promise<{ board: string }> };

async function getPosts(board: BoardSlug): Promise<{ posts: CommunityPost[]; dbError: string | null }> {
  try {
    const supabase = getSupabaseServer();
    let query = supabase
      .from('community_posts')
      .select(POST_SELECT_FIELDS)
      .eq('board', board);

    if (board === 'tips') {
      query = query.order('like_count', { ascending: false }).order('created_at', { ascending: false });
    } else {
      query = query.order('created_at', { ascending: false });
    }

    const { data, error } = await query.limit(50);
    if (error) throw error;

    return {
      posts: (data || []).map(row => ({ ...row, like_count: row.like_count ?? 0 })) as CommunityPost[],
      dbError: null,
    };
  } catch (e) {
    const msg = e instanceof Error ? e.message : '조회 실패';
    if (msg.includes('community_posts')) {
      return { posts: [], dbError: '게시판 DB가 준비되지 않았습니다. add_community.sql을 Supabase에서 실행해 주세요.' };
    }
    return { posts: [], dbError: msg };
  }
}

export default async function CommunityBoardPage({ params }: Props) {
  const { board } = await params;
  if (!isBoardSlug(board)) notFound();

  const meta = BOARDS[board];
  const Icon = meta.icon;
  const { posts, dbError } = await getPosts(board);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <Link
        href="/community"
        className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:hover:text-white mb-6"
      >
        <ChevronLeft className="w-4 h-4 mr-1" />
        커뮤니티 홈
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${meta.accent} flex items-center justify-center`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{meta.label}</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{meta.description}</p>
          </div>
        </div>
        <WritePostForm board={board} />
      </div>

      <div className="mb-6">
        <CommunityBoardNav active={board} />
      </div>

      {board === 'tips' && !dbError && (
        <p className="mb-4 text-sm text-violet-600 dark:text-violet-400">
          따봉이 많은 순으로 정렬됩니다.
        </p>
      )}

      {dbError && (
        <div className="mb-4 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
          {dbError}
        </div>
      )}

      <PostList posts={posts} board={board} />
    </div>
  );
}
