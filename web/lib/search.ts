import { getSetShortName } from '@/lib/set-names';

/** 검색어·카드명 비교 시 공백 무시 (예: "메가 다크라이" → "메가다크라이") */
export function compactSearchText(text: string): string {
  return text.trim().toLowerCase().replace(/\s+/g, '');
}

export function matchesSearchQuery(haystack: string, query: string): boolean {
  const q = compactSearchText(query);
  if (!q) return true;
  return compactSearchText(haystack).includes(q);
}

/** Supabase ilike 패턴 — 공백 제거 후 부분 일치 */
export function searchIlikePattern(query: string): string {
  const compact = query.trim().replace(/\s+/g, '');
  return `%${compact}%`;
}

/** 세트 코드·짧은 이름·DB 이름으로 검색어 매칭 */
export function setMatchesSearchQuery(
  setCode: string,
  query: string,
  dbName?: string | null,
): boolean {
  if (!query.trim()) return true;
  const names = [
    setCode,
    getSetShortName(setCode),
    dbName || '',
  ];
  return names.some(n => n && matchesSearchQuery(n, query));
}

export function filterSetCodesByQuery(setCodes: readonly string[], query: string): string[] {
  return setCodes.filter(code => setMatchesSearchQuery(code, query));
}
