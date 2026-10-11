import type { SupabaseClient } from '@supabase/supabase-js';

/** 한국시간 달력 날짜 YYYY-MM-DD */
export function kstDateString(now = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

function isMissingRelation(err: unknown, table: string): boolean {
  if (!err || typeof err !== 'object') return false;
  const e = err as { code?: string; message?: string };
  if (e.code === '42P01' || e.code === 'PGRST205') return true;
  return String(e.message || '').includes(table);
}

/** 오늘(KST) 조회수 +1. 테이블이 없으면 조용히 넘긴다. */
export async function incrementDailyView(
  supabase: SupabaseClient,
  table: 'card_view_days' | 'set_view_days',
  idColumn: 'card_id' | 'set_id',
  id: number,
): Promise<void> {
  const viewDate = kstDateString();
  const { data, error } = await supabase
    .from(table)
    .select('view_count')
    .eq(idColumn, id)
    .eq('view_date', viewDate)
    .maybeSingle();

  if (error) {
    if (isMissingRelation(error, table)) return;
    throw error;
  }

  const next = (typeof data?.view_count === 'number' ? data.view_count : 0) + 1;
  const { error: upsertError } = await supabase.from(table).upsert(
    { [idColumn]: id, view_date: viewDate, view_count: next },
    { onConflict: `${idColumn},view_date` },
  );
  if (upsertError && !isMissingRelation(upsertError, table)) throw upsertError;
}
