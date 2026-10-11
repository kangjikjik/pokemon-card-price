import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { incrementDailyView } from '@/lib/view-days';

/** 세트 페이지(박스 시세) 조회 +1 */
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
      .from('card_sets')
      .select('id')
      .eq('id', id)
      .maybeSingle();
    if (error) throw error;
    if (!data) {
      return NextResponse.json({ ok: false, error: 'not found' }, { status: 404 });
    }

    await incrementDailyView(supabase, 'set_view_days', 'set_id', id);
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('[api/sets/view] error:', err);
    return NextResponse.json({ ok: false }, { status: 500 });
  }
}
