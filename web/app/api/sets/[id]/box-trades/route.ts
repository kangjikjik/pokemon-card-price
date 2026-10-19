import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { isViewableSetCode } from '@/lib/constants';

export interface BoxTradeRecord {
  price_krw: number;
  source: string;
  fetched_at: string;
  traded_at: string;   // 실제 거래 날짜 (TS 있으면) 또는 크롤 날짜
  label: string;
  url?: string;
}

/**
 * source 포맷:
 *  신형: "bunjang:sold:PID:TS"  | "bunjang:listing:PID:TS"
 *  구형: "bunjang:sold" | "bunjang:listing" | "bunjang:sold:none"
 */
function extractPid(source: string): string | null {
  const parts = source.split(':');
  // bunjang:sold:PID[:TS] — parts[2]가 숫자여야 유효한 PID
  if (parts.length >= 3 && /^\d+$/.test(parts[2])) return parts[2];
  return null;
}

function extractTs(source: string): number | null {
  const parts = source.split(':');
  // bunjang:sold:PID:TS → parts[3]
  if (parts.length >= 4) {
    const ts = parseInt(parts[3]);
    return isNaN(ts) || ts <= 0 ? null : ts;
  }
  return null;
}

function parseBoxSource(source: string, fetchedAt: string, setNameKr: string): { label: string; url: string; traded_at: string } {
  const pid = extractPid(source);
  const ts = extractTs(source);
  const traded_at = ts ? new Date(ts * 1000).toISOString() : fetchedAt;

  if (pid) {
    return {
      label: source.includes(':sold:') ? '거래완료' : '호가',
      url: `https://bunjang.co.kr/products/${pid}`,
      traded_at,
    };
  }
  // pid 없으면 번개장터 검색 URL
  const query = encodeURIComponent(`${setNameKr} 박스 미개봉`);
  const url = `https://bunjang.co.kr/search/products?q=${query}`;
  const label = source.includes('sold') ? '거래완료' : source.includes('listing') ? '호가' : '기타';
  return { label, url, traded_at };
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const numericId = parseInt(id);
  if (isNaN(numericId)) return NextResponse.json({ error: 'invalid id' }, { status: 400 });

  const region = req.nextUrl.searchParams.get('region') || 'KR';

  try {
    const supabase = getSupabaseServer();

    // 세트 정보 + 이름 확인
    const { data: setData } = await supabase
      .from('card_sets')
      .select('id, set_code, name_kr')
      .eq('id', numericId)
      .single();

    if (!setData) return NextResponse.json({ error: 'not found' }, { status: 404 });
    if (!isViewableSetCode(setData.set_code)) {
      return NextResponse.json({ error: 'not found' }, { status: 404 });
    }

    const setNameKr = setData.name_kr || setData.set_code;

    const { data } = await supabase
      .from('prices_box')
      .select('price_krw, source, fetched_at')
      .eq('set_id', numericId)
      .eq('region', region)
      .gt('price_krw', 0)
      .or('source.like.bunjang:sold:%,source.like.bunjang:listing:%,source.like.bunjang-jp:sold:%,source.like.bunjang-jp:listing:%')
      .order('fetched_at', { ascending: false })
      .limit(30);

    const parsed: BoxTradeRecord[] = (data || [])
      .map((r) => {
        const fa = r.fetched_at || '';
        return {
          price_krw: r.price_krw,
          source: r.source || '',
          fetched_at: fa,
          ...parseBoxSource(r.source || '', fa, setNameKr),
        };
      })
      // URL 없는 거래 제외 (집계 데이터)
      .filter((r) => !!r.url && !r.url.includes('search/products'));

    const sold = parsed.filter((r) => r.label === '거래완료');
    const listing = parsed.filter((r) => r.label === '호가');
    const pool = [...sold, ...listing];

    const trades = pool
      .sort((a, b) => new Date(b.traded_at).getTime() - new Date(a.traded_at).getTime())
      .slice(0, 30);

    return NextResponse.json({ trades });
  } catch {
    return NextResponse.json({ trades: [] });
  }
}
