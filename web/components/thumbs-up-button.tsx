'use client';

import { useState } from 'react';
import { Loader2, ThumbsUp } from 'lucide-react';
import { getLikedPostIds, getVoterKey, markPostLiked } from '@/lib/community-auth';

type Props = {
  postId: number;
  initialCount: number;
};

export function ThumbsUpButton({ postId, initialCount }: Props) {
  const [count, setCount] = useState(initialCount);
  const [liked, setLiked] = useState(() => getLikedPostIds().has(postId));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleLike() {
    if (liked || loading) return;
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`/api/community/tips/${postId}/like`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voter_key: getVoterKey() }),
      });
      const json = await res.json();
      if (res.status === 409 || json.already_liked) {
        markPostLiked(postId);
        setLiked(true);
        return;
      }
      if (!res.ok) {
        setError(json.error || '따봉에 실패했습니다.');
        return;
      }
      markPostLiked(postId);
      setLiked(true);
      setCount(json.data?.like_count ?? count + 1);
    } catch {
      setError('네트워크 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={handleLike}
        disabled={liked || loading}
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all ${
          liked
            ? 'bg-violet-100 dark:bg-violet-950 text-violet-700 dark:text-violet-300 border border-violet-300 dark:border-violet-700'
            : 'bg-violet-500 hover:bg-violet-600 text-white shadow-sm hover:shadow-md'
        } disabled:opacity-80`}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <ThumbsUp className={`w-4 h-4 ${liked ? 'fill-current' : ''}`} />
        )}
        따봉 {count}
      </button>
      {liked && <span className="text-xs text-slate-400">추천해 주셔서 감사합니다!</span>}
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
}
