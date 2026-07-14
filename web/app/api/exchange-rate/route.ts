import { NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';

const FIXED_RATE = 9.50; // 고정 환율 (엔/원) — 나중에 API 연동으로 대체

export async function GET() {
  try {
    const supabase = getSupabaseServer();

    const { data, error } = await supabase
      .from('exchange_rates')
      .select('jpy_to_krw, fetched_at')
      .order('fetched_at', { ascending: false })
      .limit(1)
      .single();

    if (error) throw error;

    return NextResponse.json({
      rate: parseFloat(data.jpy_to_krw),
      fetchedAt: data.fetched_at,
      source: 'db',
    });
  } catch {
    return NextResponse.json({
      rate: FIXED_RATE,
      fetchedAt: new Date().toISOString(),
      source: 'fixed',
    });
  }
}
