'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Pencil, Trash2 } from 'lucide-react';
import type { BoardSlug, CommunityPost } from '@/lib/community';
import { getPostEditToken, removePostEditToken } from '@/lib/community-auth';

type Props = {
  board: BoardSlug;
  post: CommunityPost;
  onUpdated: (post: CommunityPost) => void;
};

export function PostOwnerActions({ board, post, onUpdated }: Props) {
  const router = useRouter();
  const editToken = getPostEditToken(post.id);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(post.title);
  const [content, setContent] = useState(post.content);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!editToken) return null;

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`/api/community/${board}/${post.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_token: editToken, title, content }),
      });
      const json = await res.json();
      if (!res.ok) {
        setError(json.error || '수정에 실패했습니다.');
        return;
      }
      onUpdated(json.data);
      setEditing(false);
      router.refresh();
    } catch {
      setError('네트워크 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!confirm('이 글을 삭제할까요?')) return;
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`/api/community/${board}/${post.id}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_token: editToken }),
      });
      const json = await res.json();
      if (!res.ok) {
        setError(json.error || '삭제에 실패했습니다.');
        return;
      }
      removePostEditToken(post.id);
      router.push(`/community/${board}`);
      router.refresh();
    } catch {
      setError('네트워크 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }

  if (editing) {
    return (
      <form onSubmit={handleUpdate} className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-800 space-y-4">
        <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">글 수정</h3>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          maxLength={200}
          required
          className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
        />
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          maxLength={5000}
          required
          rows={8}
          className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm resize-y"
        />
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={() => {
              setEditing(false);
              setTitle(post.title);
              setContent(post.content);
              setError('');
            }}
            className="px-3 py-1.5 rounded-lg text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold disabled:opacity-60"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            저장
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-800">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setEditing(true)}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          <Pencil className="w-3.5 h-3.5" />
          수정
        </button>
        <button
          type="button"
          onClick={handleDelete}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900/50 hover:bg-red-50 dark:hover:bg-red-950/30"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
          삭제
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
