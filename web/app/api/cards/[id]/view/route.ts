import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';

function isMissingViewCountError(err: unknown): boolean {
  if (err && typeof err === 'object') {
    const e = err as { code?: string; message?: string };
    if (e.code === '42703') return true;
    if (e.message?.includes('view_count')) return true;
  }
  const msg = String(err);
  return msg.includes('view_count') && (msg.includes('42703') || msg.includes('does not exist'));
}

/** 카드 상세(시세 확인) 조회수 +1 */
export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id: idStr } = await params;
  const id = parseInt(idStr, 10);
  if (!Number.isFinite(id) || id <= 0) {
    return NextResponse.json({ ok: false, error: 'invalid id' }, { status: 400 });
  }

  try {
    const supabase = getSupabaseServer();

    const { data, error } = await supabase
      .from('cards')
      .select('view_count')
      .eq('id', id)
      .maybeSingle();

    if (error) {
      if (isMissingViewCountError(error)) {
        return NextResponse.json({ ok: true, skipped: true, reason: 'view_count column missing' });
      }
      throw error;
    }
    if (!data) {
      return NextResponse.json({ ok: false, error: 'not found' }, { status: 404 });
    }

    const next = (typeof data.view_count === 'number' ? data.view_count : 0) + 1;
    const { error: updateError } = await supabase
      .from('cards')
      .update({ view_count: next })
      .eq('id', id);

    if (updateError) throw updateError;

    return NextResponse.json({ ok: true, view_count: next });
  } catch (err) {
    console.error('[api/cards/view] error:', err);
    if (isMissingViewCountError(err)) {
      return NextResponse.json({ ok: true, skipped: true, reason: 'view_count column missing' });
    }
    return NextResponse.json({ ok: false }, { status: 500 });
  }
}
