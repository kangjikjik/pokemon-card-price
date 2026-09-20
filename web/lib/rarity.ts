/** 레어도 분류 및 정렬 */

export const EXCLUDED_RARITIES = new Set([
  "U", "C", "SA", "N", "CM", "UM", "PROMO", "R",
  /** collectory: 마스터볼 미러 카드번호 접미사 M — 공식 단독 등급명 아님 */
]);

/** collectory/구 DB → 표준 등급 */
export const RARITY_ALIASES: Record<string, string> = {
  "UR-ex": "SR",
  IR: "AR",
  /** 나무위키 𖤓 빛나는 전설 */
  Shining: "SL",
  SHINING: "SL",
};

export function normalizeRarity(rarity: string): string {
  const r = (rarity || "").trim();
  return RARITY_ALIASES[r] ?? r;
}

/** 목록·검색 노출 최소 등급 — RR 이상 히트 카드 (RARITY_RANK.RR과 동일) */
export const MIN_DISPLAY_RARITY_RANK = 10;

export function isPromoRarity(rarity: string): boolean {
  return normalizeRarity(rarity) === "P";
}

export function isDisplayableRarity(rarity: string): boolean {
  const norm = normalizeRarity(rarity);
  if (isPromoRarity(norm)) return true;
  if (EXCLUDED_RARITIES.has(norm)) return false;
  return rankForRarity(norm) >= MIN_DISPLAY_RARITY_RANK;
}

/** 등급 한글명 */
export const RARITY_LABELS: Record<string, string> = {
  C: "커먼",
  U: "언커먼",
  R: "레어",
  RR: "더블레어",
  SR: "슈퍼레어",
  AR: "아트레어",
  SAR: "스페셜아트레어",
  UR: "울트라레어",
  ACE: "에이스스펙",
  BWR: "블랙화이트레어",
  MUR: "메가울트라레어",
  MA: "메가어택레어",
  FUR: "퓨처울트라레어",
  H: "홀로",
  HR: "하이퍼레어",
  RM: "마스터볼 미러",
  SL: "빛나는",
  PR: "프리즘스타",
  TR: "트레이너스레어",
  RRR: "트리플레어",
  A: "어메이징",
  CHR: "캐릭터레어",
  CSR: "캐릭터슈퍼레어",
  K: "찬란",
  S: "샤이니",
  SSR: "샤이닝슈퍼레어",
  P: "프로모",
};

/**
 * 등급순 (높을수록 상위)
 * 히트: UR/HR/… > PR(프리즘) > SR > … > RR
 */
export const RARITY_RANK: Record<string, number> = {
  FUR: 31,
  MUR: 30,
  UR: 29,
  BWR: 28,
  SAR: 27,
  MA: 26,
  SR: 25,
  ACE: 24,
  AR: 23,
  SSR: 22,
  HR: 21,
  CSR: 20,
  /** 프리즘스타 — SR보다 위 */
  PR: 19,
  CHR: 18,
  RRR: 17,
  A: 16,
  K: 15,
  S: 14,
  TR: 13,
  SL: 12,
  H: 11,
  /** 더블레어 — 히트 중 가장 낮음 */
  RR: 10,
  /** 포켓몬 카드 151 마스터볼 미러 */
  RM: 11,
  R: 3,
  U: 2,
  C: 1,
  P: 0,
};

/** 현 등급 필터·정렬 순서: MUR → RR */
const CURRENT_RARITIES = ["MUR", "UR", "BWR", "SAR", "MA", "SR", "ACE", "AR", "RM", "RR"] as const;
const LEGACY_RARITIES = ["SSR", "HR", "CSR", "CHR", "RRR", "A", "K", "S", "PR", "TR", "P"] as const;

function sortByRarityDesc(codes: readonly string[]): string[] {
  return [...codes].sort((a, b) => (RARITY_RANK[b] ?? -1) - (RARITY_RANK[a] ?? -1));
}

export type RarityFilterGroup = {
  id: "current" | "legacy";
  title: string;
  subtitle: string;
  rarities: readonly string[];
};

/**
 * 모든 카드 필터 — 희귀한 순서 (높은 등급 먼저)
 */
export const RARITY_FILTER_GROUPS: readonly RarityFilterGroup[] = [
  {
    id: "current",
    title: "현 등급",
    subtitle: "",
    rarities: sortByRarityDesc(CURRENT_RARITIES),
  },
  {
    id: "legacy",
    title: "과거 등급",
    subtitle: "",
    rarities: sortByRarityDesc(LEGACY_RARITIES),
  },
] as const;

/** 필터에 쓰는 전체 등급 (현 → 과거 순) */
export const ALL_FILTER_RARITIES: readonly string[] = RARITY_FILTER_GROUPS.flatMap(g => [...g.rarities]);

/** 카드 목록에 실제 노출되는 등급 */
export const DISPLAY_RARITIES = ALL_FILTER_RARITIES.filter(
  code => isDisplayableRarity(code),
) as readonly string[];

export const RARITY_SORT_ORDER = [...ALL_FILTER_RARITIES].reverse();

/** @deprecated RARITY_LABELS 사용 */
export const RARITY_GROUP_LABELS = RARITY_LABELS;

export function getRarityLabel(code: string): string {
  return RARITY_LABELS[normalizeRarity(code)] ?? code;
}

export function rankForRarity(rarity: string): number {
  return RARITY_RANK[normalizeRarity(rarity)] ?? -1;
}

function rarityLabelIndex(rarity: string): number {
  const norm = normalizeRarity(rarity);
  const idx = RARITY_SORT_ORDER.indexOf(norm);
  return idx === -1 ? 999 : idx;
}

export function compareCardsByRarity(
  a: { rarity: string; rarityRank?: number; setCode?: string; number?: string; name?: string; imageUrl?: string },
  b: { rarity: string; rarityRank?: number; setCode?: string; number?: string; name?: string; imageUrl?: string },
): number {
  // 코드 기준 순위만 사용 (DB rarity_rank 스테일 방지)
  const rankA = rankForRarity(a.rarity);
  const rankB = rankForRarity(b.rarity);
  if (rankB !== rankA) return rankB - rankA;

  const labelCmp = rarityLabelIndex(b.rarity) - rarityLabelIndex(a.rarity);
  if (labelCmp !== 0) return labelCmp;

  const aHasImg = a.imageUrl ? 1 : 0;
  const bHasImg = b.imageUrl ? 1 : 0;
  if (bHasImg !== aHasImg) return bHasImg - aHasImg;

  const setCmp = (a.setCode || "").localeCompare(b.setCode || "");
  if (setCmp !== 0) return setCmp;

  const numA = parseInt((a.number || "").split("/")[0], 10) || 0;
  const numB = parseInt((b.number || "").split("/")[0], 10) || 0;
  if (numA !== numB) return numA - numB;

  return (a.name || "").localeCompare(b.name || "", "ko");
}
