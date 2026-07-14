'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { KeyRound, Loader2, PenLine } from 'lucide-react';
import type { BoardSlug } from '@/lib/community';
import {
  getCommunityAdminToken,
  saveCommunityAdminToken,
  savePostEditToken,
} from '@/lib/community-auth';

const ADMIN_HEADER = 'x-community-admin-token';

type Props = {
  board: BoardSlug;
};

export function WritePostForm({ board }: Props) {
  const router = useRouter();
  const isNotice = board === 'notice';
  const [open, setOpen] = useState(false);
  const [adminReady, setAdminReady] = useState(!isNotice);
  const [adminTokenInput, setAdminTokenInput] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isNotice) {
      setAdminReady(!!getCommunityAdminToken());
    }
  }, [isNotice]);

  async function verifyAdmin() {
    setError('');
    setLoading(true);
    try {
      const token = adminTokenInput.trim();
      if (!token) {
        setError('관리자 토큰을 입력하세요.');
        return;
      }
      const res = await fetch('/api/community/admin/verify', {
        method: 'POST',
        headers: { [ADMIN_HEADER]: token },
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        setError(json.error || '인증에 실패했습니다.');
        return;
      }
      saveCommunityAdminToken(token);
      setAdminReady(true);
      setAdminTokenInput('');
      setOpen(true);
    } catch {
      setError('네트워크 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (isNotice) {
        const token = getCommunityAdminToken();
        if (!token) {
          setError('관리자 인증이 필요합니다.');
          return;
        }
        headers[ADMIN_HEADER] = token;
      }

      const res = await fetch(`/api/community/${board}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          author_name: isNotice ? '운영자' : authorName,
          title,
          content,
        }),
      });
      const json = await res.json();
      if (!res.ok) {
        setError(json.error || '등록에 실패했습니다.');
        return;
      }
      if (json.data?.id && json.edit_token) {
        savePostEditToken(json.data.id, json.edit_token);
      }
      setOpen(false);
      setTitle('');
      setContent('');
      router.refresh();
      if (json.data?.id) {
        router.push(`/community/${board}/${json.data.id}`);
      }
    } catch {
      setError('네트워크 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }

  if (isNotice && !adminReady) {
    return (
      <div className="flex flex-col items-end gap-2">
        <button
          type="button"
          onClick={() => setOpen(v => !v)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-rose-500 hover:bg-rose-600 text-white font-bold text-sm transition-colors shadow-sm"
        >
          <KeyRound className="w-4 h-4" />
          관리자 글쓰기
        </button>
        {open && (
          <div className="w-full sm:w-80 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm space-y-3">
            <p className="text-xs text-slate-500 dark:text-slate-400">공지는 관리자만 작성할 수 있습니다.</p>
            <input
              type="password"
              value={adminTokenInput}
              onChange={e => setAdminTokenInput(e.target.value)}
              placeholder="관리자 토큰"
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
            />
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <button
              type="button"
              onClick={verifyAdmin}
              disabled={loading}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-rose-500 hover:bg-rose-600 text-white font-bold text-sm disabled:opacity-60"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              인증
            </button>
          </div>
        )}
      </div>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-white font-bold text-sm transition-colors shadow-sm ${
          isNotice ? 'bg-rose-500 hover:bg-rose-600' : 'bg-amber-500 hover:bg-amber-600'
        }`}
      >
        <PenLine className="w-4 h-4" />
        글쓰기
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4 shadow-sm"
    >
      <h3 className="text-lg font-bold text-slate-900 dark:text-white">새 글 작성</h3>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        {isNotice
          ? '공지 게시판 — 관리자만 작성할 수 있습니다.'
          : '이 브라우저에서 작성한 글만 수정·삭제할 수 있습니다.'}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {!isNotice && (
          <label className="block sm:col-span-1">
            <span className="text-sm font-medium text-slate-600 dark:text-slate-400">닉네임</span>
            <input
              value={authorName}
              onChange={e => setAuthorName(e.target.value)}
              maxLength={30}
              required
              className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
              placeholder="2~30자"
            />
          </label>
        )}
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium text-slate-600 dark:text-slate-400">제목</span>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            maxLength={200}
            required
            className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
            placeholder="제목을 입력하세요"
          />
        </label>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium text-slate-600 dark:text-slate-400">내용</span>
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            maxLength={5000}
            required
            rows={6}
            className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm resize-y min-h-[140px]"
            placeholder="내용을 입력하세요"
          />
        </label>
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          취소
        </button>
        <button
          type="submit"
          disabled={loading}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white font-bold text-sm disabled:opacity-60 ${
            isNotice ? 'bg-rose-500 hover:bg-rose-600' : 'bg-amber-500 hover:bg-amber-600'
          }`}
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          등록
        </button>
      </div>
    </form>
  );
}
