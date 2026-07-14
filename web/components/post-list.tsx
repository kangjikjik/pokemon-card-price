import Link from 'next/link';
import { Eye, ThumbsUp } from 'lucide-react';
import { formatPostDate, type BoardSlug, type CommunityPost } from '@/lib/community';

export function PostList({ posts, board }: { posts: CommunityPost[]; board: BoardSlug }) {
  if (posts.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500 dark:text-slate-400 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
        아직 게시글이 없습니다. 첫 글을 작성해 보세요.
      </div>
    );
  }

  return (
    <div className="divide-y divide-slate-100 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900">
      {posts.map(post => (
        <Link
          key={post.id}
          href={`/community/${board}/${post.id}`}
          className="block px-4 py-4 hover:bg-slate-50 dark:hover:bg-slate-950/80 transition-colors group"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h3 className="font-bold text-slate-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors truncate">
                {post.title}
              </h3>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 line-clamp-2">
                {post.content}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                <span>{post.author_name}</span>
                <span>{formatPostDate(post.created_at)}</span>
              </div>
            </div>
            <div className="flex flex-col items-end gap-1 text-xs text-slate-400 shrink-0 pt-1">
              {board === 'tips' && (
                <div className="inline-flex items-center gap-1 text-violet-500 dark:text-violet-400 font-medium">
                  <ThumbsUp className="w-3.5 h-3.5" />
                  {post.like_count ?? 0}
                </div>
              )}
              <div className="inline-flex items-center gap-1">
                <Eye className="w-3.5 h-3.5" />
                {post.view_count}
              </div>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
