import { NextRequest, NextResponse } from 'next/server';
import { randomUUID } from 'crypto';
import { getSupabaseServer } from '@/lib/supabase';
import { isBoardSlug, POST_SELECT_FIELDS, type BoardSlug, type CommunityPost } from '@/lib/community';

type Params = { params: Promise<{ board: string }> };

function validatePostBody(body: unknown): { title: string; content: string; author_name: string } | string {
  if (!body || typeof body !== 'object') return '잘못된 요청입니다.';
  const { title, content, author_name } = body as Record<string, unknown>;
  const t = String(title ?? '').trim();
  const c = String(content ?? '').trim();
  const a = String(author_name ?? '').trim();
  if (a.length < 2 || a.length > 30) return '닉네임은 2~30자입니다.';
  if (t.length < 2 || t.length > 200) return '제목은 2~200자입니다.';
  if (c.length < 2 || c.length > 5000) return '내용은 2~5000자입니다.';
  return { title: t, content: c, author_name: a };
}

function dbUnavailable(msg: string) {
  if (msg.includes('community_posts') || msg.includes('community_post_likes')) {
    return NextResponse.json(
      { error: '게시판 DB가 아직 준비되지 않았습니다. add_community_v2.sql을 실행해 주세요.' },
      { status: 503 },
    );
  }
  return null;
}

export async function GET(req: NextRequest, { params }: Params) {
  const { board } = await params;
  if (!isBoardSlug(board)) {
    return NextResponse.json({ error: '존재하지 않는 게시판입니다.' }, { status: 404 });
  }

  const page = Math.max(1, parseInt(req.nextUrl.searchParams.get('page') || '1', 10) || 1);
  const limit = Math.min(50, Math.max(1, parseInt(req.nextUrl.searchParams.get('limit') || '20', 10) || 20));
  const from = (page - 1) * limit;
  const to = from + limit - 1;

  try {
    const supabase = getSupabaseServer();
    let query = supabase
      .from('community_posts')
      .select(POST_SELECT_FIELDS, { count: 'exact' })
      .eq('board', board as BoardSlug);

    if (board === 'tips') {
      query = query.order('like_count', { ascending: false }).order('created_at', { ascending: false });
    } else {
      query = query.order('created_at', { ascending: false });
    }

    const { data, error, count } = await query.range(from, to);
    if (error) throw error;

    return NextResponse.json({
      data: (data || []).map(row => ({ ...row, like_count: row.like_count ?? 0 })) as CommunityPost[],
      page,
      limit,
      total: count ?? 0,
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : '조회 실패';
    const unavailable = dbUnavailable(msg);
    if (unavailable) return unavailable;
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function POST(req: NextRequest, { params }: Params) {
  const { board } = await params;
  if (!isBoardSlug(board)) {
    return NextResponse.json({ error: '존재하지 않는 게시판입니다.' }, { status: 404 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'JSON 형식이 올바르지 않습니다.' }, { status: 400 });
  }

  const parsed = validatePostBody(body);
  if (typeof parsed === 'string') {
    return NextResponse.json({ error: parsed }, { status: 400 });
  }

  const editToken = randomUUID();

  try {
    const supabase = getSupabaseServer();
    const { data, error } = await supabase
      .from('community_posts')
      .insert({
        board,
        title: parsed.title,
        content: parsed.content,
        author_name: parsed.author_name,
        edit_token: editToken,
        like_count: 0,
      })
      .select(POST_SELECT_FIELDS)
      .single();

    if (error) throw error;
    return NextResponse.json(
      {
        data: { ...(data as CommunityPost), like_count: data.like_count ?? 0 },
        edit_token: editToken,
      },
      { status: 201 },
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : '등록 실패';
    const unavailable = dbUnavailable(msg);
    if (unavailable) return unavailable;
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
