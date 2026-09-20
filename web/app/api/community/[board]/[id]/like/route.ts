import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { isBoardSlug, POST_SELECT_FIELDS, type CommunityPost } from '@/lib/community';

type Params = { params: Promise<{ board: string; id: string }> };

export async function POST(req: NextRequest, { params }: Params) {
  const { board, id } = await params;

  if (board !== 'tips') {
    return NextResponse.json({ error: '꿀팁 게시판에서만 따봉이 가능합니다.' }, { status: 400 });
  }
  if (!isBoardSlug(board)) {
    return NextResponse.json({ error: '존재하지 않는 게시판입니다.' }, { status: 404 });
  }

  const postId = parseInt(id, 10);
  if (Number.isNaN(postId)) {
    return NextResponse.json({ error: '잘못된 게시글 ID입니다.' }, { status: 400 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'JSON 형식이 올바르지 않습니다.' }, { status: 400 });
  }

  const voterKey = String((body as Record<string, unknown>)?.voter_key ?? '').trim();
  if (voterKey.length < 8 || voterKey.length > 64) {
    return NextResponse.json({ error: '잘못된 요청입니다.' }, { status: 400 });
  }

  try {
    const supabase = getSupabaseServer();

    const { data: post, error: postError } = await supabase
      .from('community_posts')
      .select('id, like_count')
      .eq('id', postId)
      .eq('board', 'tips')
      .single();

    if (postError || !post) {
      return NextResponse.json({ error: '게시글을 찾을 수 없습니다.' }, { status: 404 });
    }

    const { error: likeError } = await supabase
      .from('community_post_likes')
      .insert({ post_id: postId, voter_key: voterKey });

    if (likeError) {
      if (likeError.code === '23505') {
        return NextResponse.json({ error: '이미 따봉을 눌렀습니다.', already_liked: true }, { status: 409 });
      }
      if (likeError.message.includes('community_post_likes')) {
        return NextResponse.json(
          { error: '따봉 기능을 일시적으로 이용할 수 없습니다.' },
          { status: 503 },
        );
      }
      throw likeError;
    }

    const newCount = (post.like_count ?? 0) + 1;
    const { data, error } = await supabase
      .from('community_posts')
      .update({ like_count: newCount })
      .eq('id', postId)
      .select(POST_SELECT_FIELDS)
      .single();

    if (error) throw error;

    return NextResponse.json({
      data: { ...(data as CommunityPost), like_count: data.like_count ?? newCount },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : '따봉 실패';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
