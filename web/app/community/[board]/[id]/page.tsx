'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ChevronLeft, Eye, Loader2, ThumbsUp } from 'lucide-react';
import { BOARDS, formatPostDate, isBoardSlug, type BoardSlug, type CommunityPost } from '@/lib/community';
import { PostOwnerActions } from '@/components/post-owner-actions';
import { ThumbsUpButton } from '@/components/thumbs-up-button';

export default function CommunityPostPage() {
  const params = useParams();
  const board = String(params.board || '');
  const id = String(params.id || '');
  const [post, setPost] = useState<CommunityPost | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const meta = isBoardSlug(board) ? BOARDS[board] : null;

  useEffect(() => {
    if (!isBoardSlug(board) || !id) {
      setError('잘못된 경로입니다.');
      setLoading(false);
      return;
    }
    fetch(`/api/community/${board}/${id}`)
      .then(r => r.json())
      .then(json => {
        if (json.data) setPost(json.data);
        else setError(json.error || '게시글을 불러오지 못했습니다.');
      })
      .catch(() => setError('네트워크 오류가 발생했습니다.'))
      .finally(() => setLoading(false));
  }, [board, id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </div>
    );
  }

  if (error || !post || !meta) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-slate-500">{error || '게시글을 찾을 수 없습니다.'}</p>
        <Link href={isBoardSlug(board) ? `/community/${board}` : '/community'} className="text-amber-500 hover:underline mt-4 inline-block">
          목록으로
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link
        href={`/community/${board}`}
        className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:hover:text-white mb-6"
      >
        <ChevronLeft className="w-4 h-4 mr-1" />
        {meta.label}
      </Link>

      <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 md:p-8 shadow-sm">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 mb-3">
          <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-medium text-slate-600 dark:text-slate-300">
            {meta.label}
          </span>
          <span>{post.author_name}</span>
          <span>{formatPostDate(post.created_at)}</span>
          {post.updated_at && post.updated_at !== post.created_at && (
            <span className="text-slate-400">(수정됨)</span>
          )}
          <span className="inline-flex items-center gap-1">
            <Eye className="w-3.5 h-3.5" />
            {post.view_count}
          </span>
          {board === 'tips' && (
            <span className="inline-flex items-center gap-1 text-violet-500 dark:text-violet-400">
              <ThumbsUp className="w-3.5 h-3.5" />
              {post.like_count ?? 0}
            </span>
          )}
        </div>
        <h1 className="text-2xl md:text-3xl font-bold text-slate-900 dark:text-white mb-6">
          {post.title}
        </h1>
        <div className="prose prose-slate dark:prose-invert max-w-none">
          <p className="whitespace-pre-wrap text-slate-700 dark:text-slate-300 leading-relaxed">
            {post.content}
          </p>
        </div>

        {board === 'tips' && (
          <div className="mt-8">
            <ThumbsUpButton postId={post.id} initialCount={post.like_count ?? 0} />
          </div>
        )}

        <PostOwnerActions board={board as BoardSlug} post={post} onUpdated={setPost} />
      </article>
    </div>
  );
}
