import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { isBoardSlug, POST_SELECT_FIELDS, type CommunityPost } from '@/lib/community';

type Params = { params: Promise<{ board: string; id: string }> };

function dbUnavailable(msg: string) {
  if (msg.includes('community_posts')) {
    return NextResponse.json(
      { error: '게시판 서비스를 일시적으로 이용할 수 없습니다.' },
      { status: 503 },
    );
  }
  return null;
}

function parsePostId(id: string) {
  const postId = parseInt(id, 10);
  return Number.isNaN(postId) ? null : postId;
}

async function fetchOwnedPost(board: string, postId: number, editToken: string) {
  const supabase = getSupabaseServer();
  const { data, error } = await supabase
    .from('community_posts')
    .select('id, edit_token')
    .eq('id', postId)
    .eq('board', board)
    .single();

  if (error || !data) return { error: '게시글을 찾을 수 없습니다.', status: 404 as const };
  if (!data.edit_token || data.edit_token !== editToken) {
    return { error: '수정·삭제 권한이 없습니다.', status: 403 as const };
  }
  return { supabase };
}

export async function GET(req: NextRequest, { params }: Params) {
  const { board, id } = await params;
  if (!isBoardSlug(board)) {
    return NextResponse.json({ error: '존재하지 않는 게시판입니다.' }, { status: 404 });
  }

  const postId = parsePostId(id);
  if (postId === null) {
    return NextResponse.json({ error: '잘못된 게시글 ID입니다.' }, { status: 400 });
  }

  try {
    const supabase = getSupabaseServer();
    const { data, error } = await supabase
      .from('community_posts')
      .select(POST_SELECT_FIELDS)
      .eq('id', postId)
      .eq('board', board)
      .single();

    if (error || !data) {
      return NextResponse.json({ error: '게시글을 찾을 수 없습니다.' }, { status: 404 });
    }

    if (req.nextUrl.searchParams.get('view') !== '0') {
      await supabase
        .from('community_posts')
        .update({ view_count: (data.view_count || 0) + 1 })
        .eq('id', postId);
    }

    return NextResponse.json({
      data: {
        ...data,
        view_count: (data.view_count || 0) + 1,
        like_count: data.like_count ?? 0,
      } as CommunityPost,
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : '조회 실패';
    const unavailable = dbUnavailable(msg);
    if (unavailable) return unavailable;
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function PATCH(req: NextRequest, { params }: Params) {
  const { board, id } = await params;
  if (!isBoardSlug(board)) {
    return NextResponse.json({ error: '존재하지 않는 게시판입니다.' }, { status: 404 });
  }

  const postId = parsePostId(id);
  if (postId === null) {
    return NextResponse.json({ error: '잘못된 게시글 ID입니다.' }, { status: 400 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'JSON 형식이 올바르지 않습니다.' }, { status: 400 });
  }

  const { edit_token, title, content } = (body || {}) as Record<string, unknown>;
  const token = String(edit_token ?? '').trim();
  const t = String(title ?? '').trim();
  const c = String(content ?? '').trim();

  if (!token) return NextResponse.json({ error: '수정 권한이 없습니다.' }, { status: 403 });
  if (t.length < 2 || t.length > 200) return NextResponse.json({ error: '제목은 2~200자입니다.' }, { status: 400 });
  if (c.length < 2 || c.length > 5000) return NextResponse.json({ error: '내용은 2~5000자입니다.' }, { status: 400 });

  try {
    const owned = await fetchOwnedPost(board, postId, token);
    if ('error' in owned) {
      return NextResponse.json({ error: owned.error }, { status: owned.status });
    }

    const { data, error } = await owned.supabase
      .from('community_posts')
      .update({ title: t, content: c, updated_at: new Date().toISOString() })
      .eq('id', postId)
      .select(POST_SELECT_FIELDS)
      .single();

    if (error) throw error;
    return NextResponse.json({
      data: { ...(data as CommunityPost), like_count: data.like_count ?? 0 },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : '수정 실패';
    const unavailable = dbUnavailable(msg);
    if (unavailable) return unavailable;
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest, { params }: Params) {
  const { board, id } = await params;
  if (!isBoardSlug(board)) {
    return NextResponse.json({ error: '존재하지 않는 게시판입니다.' }, { status: 404 });
  }

  const postId = parsePostId(id);
  if (postId === null) {
    return NextResponse.json({ error: '잘못된 게시글 ID입니다.' }, { status: 400 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'JSON 형식이 올바르지 않습니다.' }, { status: 400 });
  }

  const token = String((body as Record<string, unknown>)?.edit_token ?? '').trim();
  if (!token) return NextResponse.json({ error: '삭제 권한이 없습니다.' }, { status: 403 });

  try {
    const owned = await fetchOwnedPost(board, postId, token);
    if ('error' in owned) {
      return NextResponse.json({ error: owned.error }, { status: owned.status });
    }

    const { error } = await owned.supabase.from('community_posts').delete().eq('id', postId);
    if (error) throw error;
    return NextResponse.json({ ok: true });
  } catch (e) {
    const msg = e instanceof Error ? e.message : '삭제 실패';
    const unavailable = dbUnavailable(msg);
    if (unavailable) return unavailable;
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
